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


# ── test_transcribe_audio_empty_input ─────────────────────────────────────────


@pytest.mark.unit
class TestTranscribeAudioEmptyInput:
    async def test_local_provider_empty_bytes_does_not_crash(self, monkeypatch):
        """transcribe_audio with provider='local' and empty bytes must not
        raise; it returns the executor result (even if it is an empty string)."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "local")

        async def fake_run_in_executor(executor, func, *args):
            # Simulate faster-whisper returning no segments for silent audio
            return ""

        mock_loop = MagicMock()
        mock_loop.run_in_executor = fake_run_in_executor

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            result = await transcribe_audio(b"")

        assert result == ""

    async def test_openai_provider_empty_bytes_does_not_crash(self, monkeypatch):
        """transcribe_audio with provider='openai' and empty bytes must not
        raise; it wraps the bytes in BytesIO and returns the API response."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "openai")
        monkeypatch.setattr(stt_module.settings, "openai_api_key", "sk-test")

        async def fake_create(**kwargs):
            return ""

        mock_transcriptions = MagicMock()
        mock_transcriptions.create = fake_create
        mock_audio = MagicMock()
        mock_audio.transcriptions = mock_transcriptions
        mock_client = MagicMock()
        mock_client.audio = mock_audio
        mock_async_openai = MagicMock(return_value=mock_client)

        fake_openai = MagicMock()
        fake_openai.AsyncOpenAI = mock_async_openai

        with patch.dict("sys.modules", {"openai": fake_openai}):
            result = await transcribe_audio(b"")

        # Should return empty string (stripped result of "")
        assert result == ""


# ── test_transcribe_sync_audio_stream ─────────────────────────────────────────


@pytest.mark.unit
class TestTranscribeSyncAudioStream:
    def test_wraps_audio_bytes_in_bytesio(self, monkeypatch):
        """_transcribe_sync must pass a BytesIO-wrapped version of the raw
        audio_bytes to model.transcribe, not the raw bytes directly."""
        captured_call_args: list = []

        mock_model = MagicMock()

        def capture_transcribe(audio_stream, **kwargs):
            captured_call_args.append(audio_stream)
            return (iter([]), MagicMock())

        mock_model.transcribe = capture_transcribe
        monkeypatch.setattr(stt_module, "_whisper_model", mock_model)

        raw = b"binary-audio-data-xyz"
        _transcribe_sync(raw)

        assert len(captured_call_args) == 1
        stream = captured_call_args[0]
        # Must be a BytesIO (or compatible file-like object), not raw bytes
        assert isinstance(stream, io.BytesIO)
        # The stream must contain the original bytes
        assert stream.read() == raw

    def test_bytesio_is_seeked_to_start(self, monkeypatch):
        """The BytesIO passed to transcribe must be seeked to position 0 so
        faster-whisper can read from the beginning."""
        captured_streams: list = []

        mock_model = MagicMock()

        def capture_transcribe(audio_stream, **kwargs):
            captured_streams.append(audio_stream)
            return (iter([]), MagicMock())

        mock_model.transcribe = capture_transcribe
        monkeypatch.setattr(stt_module, "_whisper_model", mock_model)

        _transcribe_sync(b"some-audio")

        stream = captured_streams[0]
        # After transcribe receives it, tell() should be at 0 (just opened)
        # OR the content must match the original bytes when read from current pos
        stream.seek(0)
        assert stream.read() == b"some-audio"


# ── test_transcribe_audio_openai_strips_result ────────────────────────────────


@pytest.mark.unit
class TestTranscribeAudioOpenAIStripsResult:
    async def test_strips_leading_trailing_whitespace(self, monkeypatch):
        """The text returned by the OpenAI transcription endpoint must have
        leading and trailing whitespace stripped before being returned."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "openai")
        monkeypatch.setattr(stt_module.settings, "openai_api_key", "sk-test")

        raw_api_response = "  \n diente 16 caries proximal \n  "

        async def fake_create(**kwargs):
            return raw_api_response

        mock_transcriptions = MagicMock()
        mock_transcriptions.create = fake_create
        mock_audio = MagicMock()
        mock_audio.transcriptions = mock_transcriptions
        mock_client = MagicMock()
        mock_client.audio = mock_audio
        mock_async_openai = MagicMock(return_value=mock_client)

        fake_openai = MagicMock()
        fake_openai.AsyncOpenAI = mock_async_openai

        with patch.dict("sys.modules", {"openai": fake_openai}):
            result = await transcribe_audio(b"audio-bytes")

        assert result == "diente 16 caries proximal"

    async def test_strips_tab_characters(self, monkeypatch):
        """Tab characters at the boundaries of the API response must also be
        stripped."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "openai")
        monkeypatch.setattr(stt_module.settings, "openai_api_key", "sk-test")

        raw_api_response = "\t\tperiodontitis moderada\t"

        async def fake_create(**kwargs):
            return raw_api_response

        mock_transcriptions = MagicMock()
        mock_transcriptions.create = fake_create
        mock_audio = MagicMock()
        mock_audio.transcriptions = mock_transcriptions
        mock_client = MagicMock()
        mock_client.audio = mock_audio
        mock_async_openai = MagicMock(return_value=mock_client)

        fake_openai = MagicMock()
        fake_openai.AsyncOpenAI = mock_async_openai

        with patch.dict("sys.modules", {"openai": fake_openai}):
            result = await transcribe_audio(b"audio")

        assert result == "periodontitis moderada"

    async def test_already_stripped_result_unchanged(self, monkeypatch):
        """A result with no surrounding whitespace is returned as-is."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "openai")
        monkeypatch.setattr(stt_module.settings, "openai_api_key", "sk-test")

        clean_response = "absceso periapical diente 46"

        async def fake_create(**kwargs):
            return clean_response

        mock_transcriptions = MagicMock()
        mock_transcriptions.create = fake_create
        mock_audio = MagicMock()
        mock_audio.transcriptions = mock_transcriptions
        mock_client = MagicMock()
        mock_client.audio = mock_audio
        mock_async_openai = MagicMock(return_value=mock_client)

        fake_openai = MagicMock()
        fake_openai.AsyncOpenAI = mock_async_openai

        with patch.dict("sys.modules", {"openai": fake_openai}):
            result = await transcribe_audio(b"audio")

        assert result == clean_response


# ── test_local_provider_logs_char_count ───────────────────────────────────────


@pytest.mark.unit
class TestLocalProviderLogsCharCount:
    async def test_char_count_logged(self, monkeypatch):
        """transcribe_audio (local provider) must emit a log record
        containing the character count of the transcribed text."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "local")

        transcribed_text = "diente 26 amalgama oclusal"  # 26 chars

        async def fake_run_in_executor(executor, func, *args):
            return transcribed_text

        mock_loop = MagicMock()
        mock_loop.run_in_executor = fake_run_in_executor

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            with patch.object(stt_module.logger, "info") as mock_info:
                await transcribe_audio(b"audio")

        # logger.info("Local STT completed: %d chars", len(text))
        all_info_calls = " ".join(str(c) for c in mock_info.call_args_list)
        char_count = str(len(transcribed_text))
        assert char_count in all_info_calls, (
            f"Expected an info log containing the char count ({char_count}). "
            f"Info calls: {mock_info.call_args_list}"
        )

    async def test_char_count_matches_actual_result_length(self, monkeypatch):
        """The character count logged must match len(text)."""
        monkeypatch.setattr(stt_module.settings, "voice_stt_provider", "local")

        transcribed_text = "texto con exactamente cuarenta y seis caracteres ok"
        expected_count = len(transcribed_text)

        logged_messages: list[str] = []

        async def fake_run_in_executor(executor, func, *args):
            return transcribed_text

        mock_loop = MagicMock()
        mock_loop.run_in_executor = fake_run_in_executor

        def capture_info(msg, *args, **kwargs):
            logged_messages.append(str(msg) % args if args else str(msg))

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            with patch.object(stt_module.logger, "info", side_effect=capture_info):
                result = await transcribe_audio(b"audio")

        assert result == transcribed_text
        combined = " ".join(logged_messages)
        assert str(expected_count) in combined
