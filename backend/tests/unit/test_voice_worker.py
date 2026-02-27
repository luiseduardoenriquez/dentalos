"""Unit tests for VoiceWorker (app/workers/voice_worker.py).

Tests cover:
  - Non-voice job types are skipped without processing
  - Missing transcription_id returns early
  - Missing s3_key returns early (H5)
  - Invalid schema name skips processing (H6)
  - Success path: downloads audio, transcribes, updates DB record
  - duration_seconds is set to None on success (H8)
  - Transcription not found in DB returns without error
  - Error path marks transcription as failed before re-raising (C3)
  - UUID conversion: transcription_id is properly cast to UUID (M3)
  - Schema name construction: 'tn_' prefix added only when not already present
  - _mark_transcription_failed is best-effort: internal errors are logged, not raised
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.queue import QueueMessage
from app.workers.voice_worker import VoiceWorker


# ── helpers ───────────────────────────────────────────────────────────────────

_TENANT_ID = "abc123"
_TRANSCRIPTION_UUID = uuid.uuid4()
_S3_KEY = "abc123/patient-456/voice/clip.webm"
_TRANSCRIBED_TEXT = "diente 36 con caries oclusal profunda"


def _make_message(**overrides) -> QueueMessage:
    """Return a valid voice.transcribe QueueMessage."""
    base = {
        "tenant_id": _TENANT_ID,
        "job_type": "voice.transcribe",
        "payload": {
            "transcription_id": str(_TRANSCRIPTION_UUID),
            "s3_key": _S3_KEY,
        },
    }
    base.update(overrides)
    return QueueMessage(**base)


def _mock_select():
    """Return a mock for sqlalchemy.select that chains .where() properly."""
    mock_query = MagicMock()
    mock_query.where.return_value = mock_query  # chaining
    mock_select_fn = MagicMock(return_value=mock_query)
    return mock_select_fn


def _make_db_context(transcription_obj=None):
    """Return a mock async context manager that simulates AsyncSessionLocal.

    The returned context manager yields a mock db session whose execute()
    returns a result whose scalar_one_or_none() gives transcription_obj.
    """
    mock_db = AsyncMock()

    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = transcription_obj

    mock_db.execute = AsyncMock(return_value=scalar_result)
    mock_db.commit = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_db)
    cm.__aexit__ = AsyncMock(return_value=False)

    async_session_local = MagicMock(return_value=cm)
    return async_session_local, mock_db


def _make_transcription_obj():
    """Return a minimal mock object mimicking a VoiceTranscription ORM row."""
    obj = MagicMock()
    obj.status = "processing"
    obj.text = None
    obj.duration_seconds = 42  # Will be overwritten to None on success (H8)
    return obj



# ── TestVoiceWorkerSkipsNonVoiceJobs ──────────────────────────────────────────


@pytest.mark.unit
class TestVoiceWorkerSkipsNonVoiceJobs:
    async def test_non_voice_job_type_returns_without_processing(self):
        """Messages with job_type != 'voice.transcribe' must be silently ignored."""
        worker = VoiceWorker()
        msg = QueueMessage(
            tenant_id=_TENANT_ID,
            job_type="clinical.pdf",
            payload={"transcription_id": str(_TRANSCRIPTION_UUID), "s3_key": _S3_KEY},
        )

        with patch("app.core.storage.storage_client") as mock_storage:
            await worker.process(msg)
            mock_storage.download_file.assert_not_called()

    async def test_notification_job_type_also_skipped(self):
        """Any unrelated job_type is ignored, not just 'clinical.pdf'."""
        worker = VoiceWorker()
        msg = QueueMessage(tenant_id=_TENANT_ID, job_type="email.send", payload={})
        await worker.process(msg)


# ── TestVoiceWorkerEarlyReturns ───────────────────────────────────────────────


@pytest.mark.unit
class TestVoiceWorkerEarlyReturns:
    async def test_missing_transcription_id_returns_early(self):
        """A voice.transcribe message with no transcription_id must return early."""
        worker = VoiceWorker()
        msg = _make_message()
        msg.payload.pop("transcription_id")

        with patch("app.core.storage.storage_client") as mock_storage:
            await worker.process(msg)
            mock_storage.download_file.assert_not_called()

    async def test_none_transcription_id_returns_early(self):
        """Explicit None transcription_id is treated same as missing."""
        worker = VoiceWorker()
        msg = _make_message()
        msg.payload["transcription_id"] = None

        with patch("app.core.storage.storage_client") as mock_storage:
            await worker.process(msg)
            mock_storage.download_file.assert_not_called()

    async def test_missing_s3_key_returns_early_h5(self):
        """H5: A message with no s3_key must return early without downloading."""
        worker = VoiceWorker()
        msg = _make_message()
        msg.payload.pop("s3_key")

        with patch("app.core.storage.storage_client") as mock_storage:
            await worker.process(msg)
            mock_storage.download_file.assert_not_called()

    async def test_empty_s3_key_returns_early(self):
        """An empty string s3_key is falsy and must trigger the early return."""
        worker = VoiceWorker()
        msg = _make_message()
        msg.payload["s3_key"] = ""

        with patch("app.core.storage.storage_client") as mock_storage:
            await worker.process(msg)
            mock_storage.download_file.assert_not_called()

    async def test_invalid_schema_name_returns_early_h6(self):
        """H6: When validate_schema_name returns False, processing must stop."""
        worker = VoiceWorker()
        msg = _make_message()
        async_session_local, mock_db = _make_db_context()

        mock_storage = MagicMock()
        mock_storage.download_file = AsyncMock(return_value=b"audio")

        with (
            patch("app.core.database.AsyncSessionLocal", async_session_local),
            patch("app.core.storage.storage_client", mock_storage),
            patch("app.core.tenant.validate_schema_name", return_value=False),
            patch("app.services.voice_stt.transcribe_audio", AsyncMock(return_value="ok")),
        ):
            await worker.process(msg)
            mock_storage.download_file.assert_not_called()


# ── TestVoiceWorkerSuccessPath ─────────────────────────────────────────────────


@pytest.mark.unit
class TestVoiceWorkerSuccessPath:
    """Test the happy path where audio is downloaded, transcribed, and saved.

    We patch sqlalchemy.select via the lazy import in the worker.
    """

    async def _run_success(self, transcription=None, stt_text=_TRANSCRIBED_TEXT):
        """Helper that runs the worker in success mode and returns (transcription, mock_db)."""
        worker = VoiceWorker()
        msg = _make_message()
        if transcription is None:
            transcription = _make_transcription_obj()
        async_session_local, mock_db = _make_db_context(transcription_obj=transcription)

        mock_storage = MagicMock()
        mock_storage.download_file = AsyncMock(return_value=b"audio-bytes")
        mock_select = _mock_select()

        with (
            patch("app.core.database.AsyncSessionLocal", async_session_local),
            patch("app.core.storage.storage_client", mock_storage),
            patch("app.core.tenant.validate_schema_name", return_value=True),
            patch("app.services.voice_stt.transcribe_audio", AsyncMock(return_value=stt_text)),
            patch("sqlalchemy.select", mock_select),
        ):
            await worker.process(msg)

        return transcription, mock_db, mock_storage

    async def test_success_updates_status_to_completed(self):
        transcription, _, _ = await self._run_success()
        assert transcription.status == "completed"

    async def test_success_sets_transcription_text(self):
        transcription, _, _ = await self._run_success()
        assert transcription.text == _TRANSCRIBED_TEXT

    async def test_success_sets_duration_seconds_to_none_h8(self):
        """H8: duration_seconds must be set to None — don't estimate from compressed bytes."""
        transcription, _, _ = await self._run_success()
        assert transcription.duration_seconds is None

    async def test_success_downloads_correct_s3_key(self):
        _, _, mock_storage = await self._run_success()
        mock_storage.download_file.assert_awaited_once_with(key=_S3_KEY)

    async def test_success_commits_db_transaction(self):
        _, mock_db, _ = await self._run_success()
        mock_db.commit.assert_awaited_once()


# ── TestVoiceWorkerTranscriptionNotFound ──────────────────────────────────────


@pytest.mark.unit
class TestVoiceWorkerTranscriptionNotFound:
    async def test_transcription_not_in_db_returns_without_error(self):
        """If scalar_one_or_none() returns None, the worker must return cleanly."""
        worker = VoiceWorker()
        msg = _make_message()
        async_session_local, mock_db = _make_db_context(transcription_obj=None)

        mock_storage = MagicMock()
        mock_storage.download_file = AsyncMock(return_value=b"audio")
        mock_select = _mock_select()

        with (
            patch("app.core.database.AsyncSessionLocal", async_session_local),
            patch("app.core.storage.storage_client", mock_storage),
            patch("app.core.tenant.validate_schema_name", return_value=True),
            patch("app.services.voice_stt.transcribe_audio", AsyncMock(return_value="ok")),
            patch("sqlalchemy.select", mock_select),
        ):
            await worker.process(msg)

        mock_db.commit.assert_not_called()


# ── TestVoiceWorkerErrorPath ──────────────────────────────────────────────────


@pytest.mark.unit
class TestVoiceWorkerErrorPath:
    async def test_exception_calls_mark_transcription_failed_c3(self):
        """C3: When processing raises, _mark_transcription_failed must be called."""
        worker = VoiceWorker()
        msg = _make_message()

        mock_storage = MagicMock()
        mock_storage.download_file = AsyncMock(side_effect=RuntimeError("S3 timeout"))

        worker._mark_transcription_failed = AsyncMock()

        with (
            patch("app.core.storage.storage_client", mock_storage),
            patch("app.core.tenant.validate_schema_name", return_value=True),
            patch("app.services.voice_stt.transcribe_audio"),
        ):
            with pytest.raises(RuntimeError, match="S3 timeout"):
                await worker.process(msg)

        worker._mark_transcription_failed.assert_awaited_once_with(
            msg, str(_TRANSCRIPTION_UUID)
        )

    async def test_exception_is_reraised_after_marking_failed(self):
        """The original exception must propagate out of process()."""
        worker = VoiceWorker()
        msg = _make_message()

        mock_storage = MagicMock()
        mock_storage.download_file = AsyncMock(side_effect=ValueError("bad key"))

        worker._mark_transcription_failed = AsyncMock()

        with (
            patch("app.core.storage.storage_client", mock_storage),
            patch("app.core.tenant.validate_schema_name", return_value=True),
            patch("app.services.voice_stt.transcribe_audio"),
        ):
            with pytest.raises(ValueError, match="bad key"):
                await worker.process(msg)


# ── TestVoiceWorkerUUIDConversion ─────────────────────────────────────────────


@pytest.mark.unit
class TestVoiceWorkerUUIDConversion:
    async def test_transcription_id_converted_to_uuid_m3(self):
        """M3: The string transcription_id from the payload must be converted to UUID."""
        worker = VoiceWorker()
        msg = _make_message()
        transcription = _make_transcription_obj()
        async_session_local, mock_db = _make_db_context(transcription_obj=transcription)

        mock_storage = MagicMock()
        mock_storage.download_file = AsyncMock(return_value=b"audio")
        mock_select = _mock_select()

        with (
            patch("app.core.database.AsyncSessionLocal", async_session_local),
            patch("app.core.storage.storage_client", mock_storage),
            patch("app.core.tenant.validate_schema_name", return_value=True),
            patch("app.services.voice_stt.transcribe_audio", AsyncMock(return_value="ok")),
            patch("sqlalchemy.select", mock_select),
        ):
            await worker.process(msg)

        # Success means UUID conversion didn't crash
        assert transcription.status == "completed"


# ── TestVoiceWorkerSchemaNameConstruction ─────────────────────────────────────


@pytest.mark.unit
class TestVoiceWorkerSchemaNameConstruction:
    async def test_adds_tn_prefix_when_missing(self):
        """tenant_id without 'tn_' prefix must get it prepended."""
        worker = VoiceWorker()
        msg = _make_message(tenant_id="abc123")

        validated_schemas: list[str] = []

        def capture_validate(name: str) -> bool:
            validated_schemas.append(name)
            return True

        transcription = _make_transcription_obj()
        async_session_local, _ = _make_db_context(transcription_obj=transcription)

        mock_storage = MagicMock()
        mock_storage.download_file = AsyncMock(return_value=b"audio")
        mock_select = _mock_select()

        with (
            patch("app.core.database.AsyncSessionLocal", async_session_local),
            patch("app.core.storage.storage_client", mock_storage),
            patch("app.core.tenant.validate_schema_name", side_effect=capture_validate),
            patch("app.services.voice_stt.transcribe_audio", AsyncMock(return_value="ok")),
            patch("sqlalchemy.select", mock_select),
        ):
            await worker.process(msg)

        assert validated_schemas[0] == "tn_abc123"

    async def test_does_not_double_prefix_when_tn_already_present(self):
        """tenant_id already prefixed with 'tn_' must NOT gain a second 'tn_'."""
        worker = VoiceWorker()
        msg = _make_message(tenant_id="tn_abc123")

        validated_schemas: list[str] = []

        def capture_validate(name: str) -> bool:
            validated_schemas.append(name)
            return True

        transcription = _make_transcription_obj()
        async_session_local, _ = _make_db_context(transcription_obj=transcription)

        mock_storage = MagicMock()
        mock_storage.download_file = AsyncMock(return_value=b"audio")
        mock_select = _mock_select()

        with (
            patch("app.core.database.AsyncSessionLocal", async_session_local),
            patch("app.core.storage.storage_client", mock_storage),
            patch("app.core.tenant.validate_schema_name", side_effect=capture_validate),
            patch("app.services.voice_stt.transcribe_audio", AsyncMock(return_value="ok")),
            patch("sqlalchemy.select", mock_select),
        ):
            await worker.process(msg)

        assert validated_schemas[0] == "tn_abc123"
        assert not validated_schemas[0].startswith("tn_tn_")


# ── TestMarkTranscriptionFailed ───────────────────────────────────────────────


@pytest.mark.unit
class TestMarkTranscriptionFailed:
    async def test_marks_status_as_failed_when_found(self):
        """_mark_transcription_failed must set status='failed' and commit."""
        worker = VoiceWorker()
        msg = _make_message()
        transcription = _make_transcription_obj()
        async_session_local, mock_db = _make_db_context(transcription_obj=transcription)
        mock_select = _mock_select()

        with (
            patch("app.core.database.AsyncSessionLocal", async_session_local),
            patch("app.core.tenant.validate_schema_name", return_value=True),
            patch("sqlalchemy.select", mock_select),
        ):
            await worker._mark_transcription_failed(msg, str(_TRANSCRIPTION_UUID))

        assert transcription.status == "failed"
        mock_db.commit.assert_awaited_once()

    async def test_best_effort_does_not_raise_on_internal_error(self):
        """If _mark_transcription_failed itself throws, it must swallow."""
        worker = VoiceWorker()
        msg = _make_message()

        boom_cm = MagicMock()
        boom_cm.__aenter__ = AsyncMock(side_effect=ConnectionError("DB gone"))
        boom_cm.__aexit__ = AsyncMock(return_value=False)
        broken_session_local = MagicMock(return_value=boom_cm)

        with (
            patch("app.core.database.AsyncSessionLocal", broken_session_local),
            patch("app.core.tenant.validate_schema_name", return_value=True),
        ):
            # Must NOT propagate the ConnectionError
            await worker._mark_transcription_failed(msg, str(_TRANSCRIPTION_UUID))

    async def test_mark_failed_skips_when_schema_invalid(self):
        """If validate_schema_name returns False, no DB session is opened."""
        worker = VoiceWorker()
        msg = _make_message()
        async_session_local, mock_db = _make_db_context()

        with (
            patch("app.core.database.AsyncSessionLocal", async_session_local),
            patch("app.core.tenant.validate_schema_name", return_value=False),
        ):
            await worker._mark_transcription_failed(msg, str(_TRANSCRIPTION_UUID))

        mock_db.execute.assert_not_called()
        mock_db.commit.assert_not_called()
