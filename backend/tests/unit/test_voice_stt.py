"""Unit tests for the voice STT service (app/services/voice_stt.py).

Tests cover:
  - Local faster-whisper dispatch via run_in_executor
  - OpenAI Whisper API dispatch
  - Invalid provider raises ValueError
  - Singleton model loading (_get_whisper_model)
  - Segment concatenation in _transcribe_sync
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.voice_stt as stt_module
from app.services.voice_stt import _transcribe_sync, transcribe_audio


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_segment(text: str) -> MagicMock:
    """Return a mock faster-whisper segment with a .text attribute."""
    seg = MagicMock()
    seg.text = text
    return seg


# ── test_transcribe_audio_local_provider ─────────────────────────────────────


@pytest.mark.unit
class TestTranscribeAudioLocalProvider:
    async def test_dispatches_to_executor(self, monkeypatch):
        """transcribe_audio with provider='local' must call _transcribe_sync
        via loop.run_in_executor, not call it directly in the async loop."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "local")

        captured_calls: list = []

        async def fake_run_in_executor(executor, func, *args):
            captured_calls.append((func, args))
            return "diente 36 con caries"

        mock_loop = MagicMock()
        mock_loop.run_in_executor = fake_run_in_executor

        audio = b"fake-audio-data"

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            result = await transcribe_audio(audio)

        assert result == "diente 36 con caries"
        assert len(captured_calls) == 1
        func, args = captured_calls[0]
        # The function dispatched must be _transcribe_sync
        assert func is _transcribe_sync
        # The audio bytes are forwarded as the first positional arg
        assert args[0] == audio

    async def test_returns_text_from_executor(self, monkeypatch):
        """Return value from executor is passed through unchanged."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "local")

        expected = "  texto con espacios  "

        async def fake_run_in_executor(executor, func, *args):
            return expected

        mock_loop = MagicMock()
        mock_loop.run_in_executor = fake_run_in_executor

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            result = await transcribe_audio(b"audio")

        assert result == expected


# ── test_transcribe_audio_openai_provider ────────────────────────────────────


@pytest.mark.unit
class TestTranscribeAudioOpenAIProvider:
    async def test_calls_openai_with_correct_params(self, monkeypatch):
        """transcribe_audio with provider='openai' must call the OpenAI
        audio.transcriptions.create endpoint with model='whisper-1' and
        language='es'."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "openai")
        monkeypatch.setattr(stt_module.settings, "openai_api_key", "sk-test-key")

        mock_transcription_result = "el paciente presenta periodontitis"

        mock_create = AsyncMock(return_value=mock_transcription_result)
        mock_transcriptions = MagicMock()
        mock_transcriptions.create = mock_create
        mock_audio = MagicMock()
        mock_audio.transcriptions = mock_transcriptions
        mock_client_instance = MagicMock()
        mock_client_instance.audio = mock_audio

        mock_async_openai = MagicMock(return_value=mock_client_instance)

        with patch.dict("sys.modules", {"openai": MagicMock(AsyncOpenAI=mock_async_openai)}):
            # Re-patch the import inside the function scope
            import openai as _openai_stub  # noqa: F401 — ensure the module exists in sys.modules

            with patch("app.services.voice_stt.openai", create=True):
                pass  # openai is imported lazily inside the function

            # Patch the openai module that gets imported inside the function
            fake_openai_module = MagicMock()
            fake_openai_module.AsyncOpenAI = mock_async_openai

            with patch.dict("sys.modules", {"openai": fake_openai_module}):
                result = await transcribe_audio(b"audio-bytes")

        assert result == mock_transcription_result.strip()
        mock_async_openai.assert_called_once_with(api_key="sk-test-key")
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["model"] == "whisper-1"
        assert call_kwargs["language"] == "es"
        assert call_kwargs["response_format"] == "text"

    async def test_audio_file_has_name_attribute(self, monkeypatch):
        """The BytesIO passed to OpenAI must have .name='audio.webm' so that
        the OpenAI client can detect the MIME type."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "openai")
        monkeypatch.setattr(stt_module.settings, "openai_api_key", "sk-test")

        captured_file = {}

        async def capture_create(**kwargs):
            captured_file["file"] = kwargs["file"]
            return "ok"

        mock_transcriptions = MagicMock()
        mock_transcriptions.create = capture_create
        mock_audio = MagicMock()
        mock_audio.transcriptions = mock_transcriptions
        mock_client = MagicMock()
        mock_client.audio = mock_audio
        mock_async_openai = MagicMock(return_value=mock_client)

        fake_openai = MagicMock()
        fake_openai.AsyncOpenAI = mock_async_openai

        with patch.dict("sys.modules", {"openai": fake_openai}):
            await transcribe_audio(b"audio")

        assert captured_file["file"].name == "audio.webm"
        assert isinstance(captured_file["file"], io.BytesIO)


# ── test_transcribe_audio_invalid_provider ───────────────────────────────────


@pytest.mark.unit
class TestTranscribeAudioInvalidProvider:
    async def test_unknown_provider_raises_value_error(self, monkeypatch):
        """An unknown provider name must raise ValueError with a helpful message."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "azure")

        with pytest.raises(ValueError, match="Unknown STT provider"):
            await transcribe_audio(b"audio")

    async def test_error_message_includes_provider_name(self, monkeypatch):
        """The ValueError message must include the actual bad provider value."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "bad_provider")

        with pytest.raises(ValueError, match="bad_provider"):
            await transcribe_audio(b"audio")


# ── test_whisper_model_singleton ─────────────────────────────────────────────


@pytest.mark.unit
class TestWhisperModelSingleton:
    def test_returns_same_instance_on_multiple_calls(self, monkeypatch):
        """_get_whisper_model must only construct the WhisperModel once even
        when called multiple times (thread-safe singleton pattern)."""
        # Reset the module-level singleton before the test
        monkeypatch.setattr(stt_module, "_whisper_model", None)
        monkeypatch.setattr(stt_module.settings, "whisper_model_size", "tiny")

        mock_model_instance = MagicMock(name="WhisperModelInstance")
        mock_whisper_cls = MagicMock(return_value=mock_model_instance)

        fake_faster_whisper = MagicMock()
        fake_faster_whisper.WhisperModel = mock_whisper_cls

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            result1 = stt_module._get_whisper_model()
            result2 = stt_module._get_whisper_model()
            result3 = stt_module._get_whisper_model()

        # Constructor called exactly once
        assert mock_whisper_cls.call_count == 1
        # All calls return the same object
        assert result1 is result2 is result3

    def test_model_constructed_with_correct_params(self, monkeypatch):
        """WhisperModel must be instantiated with device='cpu' and
        compute_type='int8', plus the configured model size."""
        monkeypatch.setattr(stt_module, "_whisper_model", None)
        monkeypatch.setattr(stt_module.settings, "whisper_model_size", "small")

        mock_model_instance = MagicMock()
        mock_whisper_cls = MagicMock(return_value=mock_model_instance)

        fake_faster_whisper = MagicMock()
        fake_faster_whisper.WhisperModel = mock_whisper_cls

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            stt_module._get_whisper_model()

        mock_whisper_cls.assert_called_once_with(
            "small",
            device="cpu",
            compute_type="int8",
        )

    def test_preloaded_model_is_returned_without_construction(self, monkeypatch):
        """If the singleton is already set, no new WhisperModel is created."""
        preloaded = MagicMock(name="PreloadedModel")
        monkeypatch.setattr(stt_module, "_whisper_model", preloaded)

        mock_whisper_cls = MagicMock()
        fake_faster_whisper = MagicMock()
        fake_faster_whisper.WhisperModel = mock_whisper_cls

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            result = stt_module._get_whisper_model()

        assert result is preloaded
        mock_whisper_cls.assert_not_called()


# ── test_transcribe_sync_concatenates_segments ───────────────────────────────


@pytest.mark.unit
class TestTranscribeSyncConcatenatesSegments:
    def test_multiple_segments_joined_with_spaces(self, monkeypatch):
        """_transcribe_sync must join all segment texts with a single space."""
        segments = [
            _make_segment("  Diente 36  "),
            _make_segment("  caries oclusal  "),
            _make_segment("  requiere amalgama  "),
        ]
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter(segments), MagicMock())

        monkeypatch.setattr(stt_module, "_whisper_model", mock_model)

        result = _transcribe_sync(b"audio")

        assert result == "Diente 36 caries oclusal requiere amalgama"

    def test_single_segment_no_extra_spaces(self, monkeypatch):
        """A single segment must be returned without leading/trailing spaces."""
        segments = [_make_segment("  periodontitis severa  ")]
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter(segments), MagicMock())

        monkeypatch.setattr(stt_module, "_whisper_model", mock_model)

        result = _transcribe_sync(b"audio")

        assert result == "periodontitis severa"

    def test_empty_segment_list_returns_empty_string(self, monkeypatch):
        """No segments → empty string (silent audio)."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([]), MagicMock())

        monkeypatch.setattr(stt_module, "_whisper_model", mock_model)

        result = _transcribe_sync(b"audio")

        assert result == ""

    def test_transcribe_called_with_correct_params(self, monkeypatch):
        """model.transcribe must receive language='es' and vad_filter=True."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([]), MagicMock())

        monkeypatch.setattr(stt_module, "_whisper_model", mock_model)

        _transcribe_sync(b"sample-audio")

        call_kwargs = mock_model.transcribe.call_args.kwargs
        assert call_kwargs.get("language") == "es"
        assert call_kwargs.get("vad_filter") is True
