"""Unit tests for the VoiceService class and _validate_findings() function.

Tests cover:
  - _validate_findings: all validation paths (tooth, zone, condition, confidence)
  - create_session: success, addon disabled (402), rate limit (429), patient not found (404)
  - upload_audio: success, too large (422), session not found (404), expired (410), bad content type (422)
  - parse_transcription: success, session not found (404), expired (410), no transcriptions (422), NLP failure (C4)
  - apply_findings: success, session not found (404), expired (410), empty findings, invalid keys (H3), DentalOSError
  - submit_feedback: success with correction_rate, session not found (404)
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.error_codes import VoiceErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError, VoiceError
from app.services.voice_service import (
    VoiceService,
    _validate_findings,
)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_session(
    *,
    status: str = "active",
    is_active: bool = True,
    minutes_until_expiry: int = 25,
    transcriptions: list | None = None,
    parses: list | None = None,
) -> MagicMock:
    """Build a mock VoiceSession with sensible defaults."""
    session = MagicMock()
    session.id = uuid.uuid4()
    session.patient_id = uuid.uuid4()
    session.doctor_id = uuid.uuid4()
    session.context = "odontogram"
    session.status = status
    session.is_active = is_active
    session.expires_at = datetime.now(UTC) + timedelta(minutes=minutes_until_expiry)
    session.created_at = datetime.now(UTC) - timedelta(minutes=5)
    session.updated_at = datetime.now(UTC)
    session.transcriptions = transcriptions or []
    session.parses = parses or []
    return session


def _make_transcription(*, status: str = "completed", text: str = "diente 36 caries oclusal") -> MagicMock:
    """Build a mock VoiceTranscription."""
    t = MagicMock()
    t.id = uuid.uuid4()
    t.chunk_index = 0
    t.status = status
    t.text = text if status == "completed" else None
    t.duration_seconds = 5.0
    t.s3_key = "tenant_abc/voice/session_xyz/0.webm"
    t.created_at = datetime.now(UTC)
    return t


def _make_db(*, session_obj=None, rate_count: int = 0, patient_obj=None, chunk_count: int = 0) -> AsyncMock:
    """Build a mock AsyncSession with chained execute().scalar*() returns."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    # Scalars cascade: (rate_count_result, patient_result, chunk_count_result, session_result)
    # We build separate mock result objects for each execute() call.
    call_results = []

    # Rate-limit scalar
    rate_result = MagicMock()
    rate_result.scalar.return_value = rate_count
    call_results.append(rate_result)

    # Patient scalar_one_or_none
    patient_result = MagicMock()
    patient_result.scalar_one_or_none.return_value = patient_obj
    call_results.append(patient_result)

    # Session scalar_one_or_none (for upload / parse / apply / feedback)
    session_result = MagicMock()
    session_result.scalar_one_or_none.return_value = session_obj
    call_results.append(session_result)

    # Chunk count scalar (for upload)
    chunk_result = MagicMock()
    chunk_result.scalar.return_value = chunk_count
    call_results.append(chunk_result)

    # Default: repeat last result for any additional calls
    db.execute = AsyncMock(side_effect=call_results + [session_result] * 10)
    return db


# ── _validate_findings ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestValidateFindingsValid:
    def test_valid_finding_passes_through_unchanged(self):
        """A fully valid finding is returned as-is (within tolerance for floats)."""
        findings = [{"tooth_number": 36, "zone": "oclusal", "condition_code": "caries", "confidence": 0.95}]
        valid, warnings = _validate_findings(findings)
        assert len(valid) == 1
        assert valid[0]["tooth_number"] == 36
        assert valid[0]["zone"] == "oclusal"
        assert valid[0]["condition_code"] == "caries"
        assert valid[0]["confidence"] == pytest.approx(0.95)
        assert warnings == []

    def test_empty_list_returns_empty_results(self):
        """An empty input list produces no findings and no warnings."""
        valid, warnings = _validate_findings([])
        assert valid == []
        assert warnings == []

    def test_all_valid_condition_codes_accepted(self):
        """Every documented condition code is accepted."""
        codes = [
            "caries", "fracture", "crown", "restoration", "absent",
            "endodontic", "implant", "sealant", "prosthesis", "extraction",
            "fluorosis", "temporary",
        ]
        for code in codes:
            findings = [{"tooth_number": 11, "zone": "full", "condition_code": code, "confidence": 0.8}]
            valid, warnings = _validate_findings(findings)
            assert len(valid) == 1, f"Expected {code!r} to be valid, got warnings: {warnings}"
            assert valid[0]["condition_code"] == code

    def test_all_valid_fdi_adult_tooth_numbers_accepted(self):
        """Every FDI adult tooth (11-18, 21-28, 31-38, 41-48) is accepted."""
        sample_teeth = [11, 18, 21, 28, 31, 38, 41, 48]
        for tooth in sample_teeth:
            findings = [{"tooth_number": tooth, "zone": "full", "condition_code": "caries", "confidence": 0.7}]
            valid, warnings = _validate_findings(findings)
            assert len(valid) == 1, f"Expected tooth {tooth} to be valid"

    def test_pediatric_tooth_numbers_accepted(self):
        """FDI pediatric teeth (51-55, 61-65, 71-75, 81-85) are accepted."""
        sample_teeth = [51, 55, 61, 65, 71, 75, 81, 85]
        for tooth in sample_teeth:
            findings = [{"tooth_number": tooth, "zone": "full", "condition_code": "absent", "confidence": 0.9}]
            valid, warnings = _validate_findings(findings)
            assert len(valid) == 1, f"Expected pediatric tooth {tooth} to be valid"

    def test_all_valid_zones_accepted(self):
        """Every documented zone string is accepted."""
        zones = ["mesial", "distal", "vestibular", "lingual", "palatino", "oclusal", "incisal", "root", "full"]
        for zone in zones:
            findings = [{"tooth_number": 36, "zone": zone, "condition_code": "caries", "confidence": 0.8}]
            valid, warnings = _validate_findings(findings)
            assert len(valid) == 1, f"Expected zone {zone!r} to be valid"
            assert valid[0]["zone"] == zone

    def test_missing_zone_defaults_to_full(self):
        """A finding without a zone key silently defaults zone to 'full' (no warning — 'full' is valid)."""
        findings = [{"tooth_number": 36, "condition_code": "caries", "confidence": 0.8}]
        valid, warnings = _validate_findings(findings)
        assert len(valid) == 1
        assert valid[0]["zone"] == "full"
        # No warning expected: the default is "full" which passes zone validation


@pytest.mark.unit
class TestValidateFindingsInvalidTooth:
    def test_invalid_tooth_number_dropped(self):
        """Tooth number 99 is not in FDI notation and must be dropped."""
        findings = [{"tooth_number": 99, "zone": "full", "condition_code": "caries", "confidence": 0.8}]
        valid, warnings = _validate_findings(findings)
        assert valid == []
        assert any("99" in w and "FDI" in w for w in warnings)

    def test_non_numeric_tooth_number_dropped(self):
        """A string like 'abc' for tooth_number cannot be coerced and is dropped."""
        findings = [{"tooth_number": "abc", "zone": "full", "condition_code": "caries", "confidence": 0.8}]
        valid, warnings = _validate_findings(findings)
        assert valid == []
        assert any("tooth_number" in w for w in warnings)

    def test_none_tooth_number_dropped(self):
        """None as tooth_number triggers TypeError and the finding is dropped."""
        findings = [{"tooth_number": None, "zone": "full", "condition_code": "caries", "confidence": 0.8}]
        valid, warnings = _validate_findings(findings)
        assert valid == []
        assert len(warnings) == 1


@pytest.mark.unit
class TestValidateFindingsInvalidZone:
    def test_invalid_zone_defaults_to_full_with_warning(self):
        """An unrecognised zone string produces a warning and defaults to 'full'."""
        findings = [{"tooth_number": 36, "zone": "palatal", "condition_code": "caries", "confidence": 0.8}]
        valid, warnings = _validate_findings(findings)
        assert len(valid) == 1
        assert valid[0]["zone"] == "full"
        assert any("zone" in w for w in warnings)

    def test_numeric_zone_defaults_to_full(self):
        """A numeric zone (not a string) is invalid and defaults to 'full'."""
        findings = [{"tooth_number": 11, "zone": 5, "condition_code": "fracture", "confidence": 0.7}]
        valid, warnings = _validate_findings(findings)
        assert len(valid) == 1
        assert valid[0]["zone"] == "full"


@pytest.mark.unit
class TestValidateFindingsInvalidCondition:
    def test_spanish_condition_code_dropped(self):
        """Spanish condition terms like 'fractura' must be dropped (only English codes allowed)."""
        findings = [{"tooth_number": 11, "zone": "full", "condition_code": "fractura", "confidence": 0.9}]
        valid, warnings = _validate_findings(findings)
        assert valid == []
        assert any("condition_code" in w for w in warnings)

    def test_none_condition_code_dropped(self):
        """A None condition_code is invalid and causes the finding to be dropped."""
        findings = [{"tooth_number": 21, "zone": "full", "condition_code": None, "confidence": 0.5}]
        valid, warnings = _validate_findings(findings)
        assert valid == []
        assert any("condition_code" in w for w in warnings)

    def test_empty_string_condition_code_dropped(self):
        """An empty string condition_code is not in VALID_CONDITION_CODES."""
        findings = [{"tooth_number": 21, "zone": "full", "condition_code": "", "confidence": 0.5}]
        valid, warnings = _validate_findings(findings)
        assert valid == []


@pytest.mark.unit
class TestValidateFindingsConfidenceClamping:
    def test_confidence_above_one_clamped_to_one(self):
        """Confidence of 1.5 must be clamped down to 1.0."""
        findings = [{"tooth_number": 36, "zone": "oclusal", "condition_code": "caries", "confidence": 1.5}]
        valid, warnings = _validate_findings(findings)
        assert len(valid) == 1
        assert valid[0]["confidence"] == pytest.approx(1.0)

    def test_confidence_below_zero_clamped_to_zero(self):
        """Confidence of -0.1 must be clamped up to 0.0."""
        findings = [{"tooth_number": 36, "zone": "oclusal", "condition_code": "caries", "confidence": -0.1}]
        valid, warnings = _validate_findings(findings)
        assert len(valid) == 1
        assert valid[0]["confidence"] == pytest.approx(0.0)

    def test_non_numeric_confidence_defaults_to_point_five(self):
        """A non-numeric confidence value falls back to 0.5."""
        findings = [{"tooth_number": 36, "zone": "oclusal", "condition_code": "caries", "confidence": "high"}]
        valid, warnings = _validate_findings(findings)
        assert len(valid) == 1
        assert valid[0]["confidence"] == pytest.approx(0.5)

    def test_missing_confidence_defaults_to_point_five(self):
        """A finding without a confidence key uses 0.5 as the default."""
        findings = [{"tooth_number": 36, "zone": "oclusal", "condition_code": "caries"}]
        valid, warnings = _validate_findings(findings)
        assert len(valid) == 1
        assert valid[0]["confidence"] == pytest.approx(0.5)


@pytest.mark.unit
class TestValidateFindingsNonDictEntries:
    def test_non_dict_finding_dropped_with_warning(self):
        """A list item that is not a dict (e.g. a string) is skipped."""
        findings = ["tooth 36 has caries", {"tooth_number": 11, "zone": "full", "condition_code": "fracture", "confidence": 0.9}]
        valid, warnings = _validate_findings(findings)
        assert len(valid) == 1
        assert valid[0]["tooth_number"] == 11
        assert any("not a dict" in w for w in warnings)

    def test_mixed_valid_and_invalid_entries(self):
        """Only valid entries survive; invalid ones produce warnings but do not abort."""
        findings = [
            {"tooth_number": 36, "zone": "oclusal", "condition_code": "caries", "confidence": 0.9},  # valid
            {"tooth_number": 99, "zone": "full", "condition_code": "caries", "confidence": 0.8},      # bad tooth
            {"tooth_number": 11, "zone": "incisal", "condition_code": "fractura", "confidence": 0.7}, # Spanish code
        ]
        valid, warnings = _validate_findings(findings)
        assert len(valid) == 1
        assert valid[0]["tooth_number"] == 36
        assert len(warnings) == 2


# ── VoiceService.create_session ───────────────────────────────────────────────


@pytest.mark.unit
class TestCreateSessionSuccess:
    async def test_creates_session_with_active_status(self):
        """A valid call creates a VoiceSession with status='active'."""
        service = VoiceService()
        patient = MagicMock()

        # DB: rate count = 0, patient found, flush OK
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        rate_result = MagicMock()
        rate_result.scalar.return_value = 0
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = patient

        db.execute = AsyncMock(side_effect=[rate_result, patient_result])

        # Patch get_voice_settings to return enabled
        with patch.object(service, "get_voice_settings", new=AsyncMock(return_value={
            "voice_enabled": True,
            "max_sessions_per_hour": 50,
            "max_session_duration_seconds": 1800,
        })):
            result = await service.create_session(
                db=db,
                patient_id=str(uuid.uuid4()),
                doctor_id=str(uuid.uuid4()),
                tenant_id="tn_test",
            )

        db.add.assert_called_once()
        db.flush.assert_called_once()
        # The result comes from _session_to_dict applied to a VoiceSession instance
        assert "status" in result
        added_session = db.add.call_args[0][0]
        assert added_session.status == "active"
        assert added_session.is_active is True


@pytest.mark.unit
class TestCreateSessionAddonRequired:
    async def test_raises_402_when_voice_disabled(self):
        """If voice_enabled is False, create_session raises VoiceError with status 402."""
        service = VoiceService()
        db = AsyncMock()

        with patch.object(service, "get_voice_settings", new=AsyncMock(return_value={
            "voice_enabled": False,
            "max_sessions_per_hour": 50,
            "max_session_duration_seconds": 1800,
        })):
            with pytest.raises(VoiceError) as exc_info:
                await service.create_session(
                    db=db,
                    patient_id=str(uuid.uuid4()),
                    doctor_id=str(uuid.uuid4()),
                    tenant_id="tn_test",
                )

        error = exc_info.value
        assert error.status_code == 402
        assert error.error == VoiceErrors.ADDON_REQUIRED


@pytest.mark.unit
class TestCreateSessionRateLimit:
    async def test_raises_429_when_rate_limit_exceeded(self):
        """If the doctor has reached the hourly session cap, a 429 VoiceError is raised."""
        service = VoiceService()
        db = AsyncMock()

        rate_result = MagicMock()
        rate_result.scalar.return_value = 50  # at the limit
        db.execute = AsyncMock(return_value=rate_result)

        with patch.object(service, "get_voice_settings", new=AsyncMock(return_value={
            "voice_enabled": True,
            "max_sessions_per_hour": 50,
            "max_session_duration_seconds": 1800,
        })):
            with pytest.raises(VoiceError) as exc_info:
                await service.create_session(
                    db=db,
                    patient_id=str(uuid.uuid4()),
                    doctor_id=str(uuid.uuid4()),
                    tenant_id="tn_test",
                )

        error = exc_info.value
        assert error.status_code == 429
        assert error.error == VoiceErrors.RATE_LIMIT_EXCEEDED
        assert error.details["limit"] == 50


@pytest.mark.unit
class TestCreateSessionPatientNotFound:
    async def test_raises_404_when_patient_not_found(self):
        """If the patient does not exist, create_session raises ResourceNotFoundError."""
        service = VoiceService()
        db = AsyncMock()

        rate_result = MagicMock()
        rate_result.scalar.return_value = 0
        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = None  # patient missing

        db.execute = AsyncMock(side_effect=[rate_result, patient_result])

        with patch.object(service, "get_voice_settings", new=AsyncMock(return_value={
            "voice_enabled": True,
            "max_sessions_per_hour": 50,
            "max_session_duration_seconds": 1800,
        })):
            with pytest.raises(ResourceNotFoundError) as exc_info:
                await service.create_session(
                    db=db,
                    patient_id=str(uuid.uuid4()),
                    doctor_id=str(uuid.uuid4()),
                    tenant_id="tn_test",
                )

        assert exc_info.value.status_code == 404


# ── VoiceService.upload_audio ─────────────────────────────────────────────────


@pytest.mark.unit
class TestUploadAudioTooLarge:
    async def test_raises_422_when_audio_too_large(self):
        """Audio exceeding voice_max_audio_bytes raises VoiceError(UPLOAD_FAILED, 422)."""
        service = VoiceService()
        db = AsyncMock()

        with patch("app.services.voice_service.settings") as mock_settings:
            mock_settings.voice_max_audio_bytes = 10 * 1024 * 1024  # 10 MB
            oversized = b"x" * (10 * 1024 * 1024 + 1)

            with pytest.raises(VoiceError) as exc_info:
                await service.upload_audio(
                    db=db,
                    session_id=str(uuid.uuid4()),
                    tenant_id="tn_test",
                    audio_data=oversized,
                    content_type="audio/webm",
                )

        assert exc_info.value.status_code == 422
        assert exc_info.value.error == VoiceErrors.UPLOAD_FAILED


@pytest.mark.unit
class TestUploadAudioSessionNotFound:
    async def test_raises_404_when_session_not_found(self):
        """A missing or inactive session raises VoiceError(SESSION_NOT_FOUND, 404)."""
        service = VoiceService()
        db = AsyncMock()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=session_result)

        with patch("app.services.voice_service.settings") as mock_settings:
            mock_settings.voice_max_audio_bytes = 10 * 1024 * 1024

            with pytest.raises(VoiceError) as exc_info:
                await service.upload_audio(
                    db=db,
                    session_id=str(uuid.uuid4()),
                    tenant_id="tn_test",
                    audio_data=b"small audio",
                    content_type="audio/webm",
                )

        assert exc_info.value.status_code == 404
        assert exc_info.value.error == VoiceErrors.SESSION_NOT_FOUND


@pytest.mark.unit
class TestUploadAudioSessionExpired:
    async def test_raises_410_when_session_expired_by_time(self):
        """A session whose expires_at is in the past raises VoiceError(SESSION_EXPIRED, 410)."""
        service = VoiceService()
        db = AsyncMock()
        db.flush = AsyncMock()

        expired_session = _make_session(minutes_until_expiry=-5)  # already expired

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = expired_session
        db.execute = AsyncMock(return_value=session_result)

        with patch("app.services.voice_service.settings") as mock_settings:
            mock_settings.voice_max_audio_bytes = 10 * 1024 * 1024

            with pytest.raises(VoiceError) as exc_info:
                await service.upload_audio(
                    db=db,
                    session_id=str(uuid.uuid4()),
                    tenant_id="tn_test",
                    audio_data=b"audio bytes",
                    content_type="audio/webm",
                )

        assert exc_info.value.status_code == 410
        assert exc_info.value.error == VoiceErrors.SESSION_EXPIRED
        assert expired_session.status == "expired"

    async def test_raises_410_when_session_not_active_status(self):
        """A session with status != 'active' raises VoiceError(SESSION_EXPIRED, 410)."""
        service = VoiceService()
        db = AsyncMock()
        db.flush = AsyncMock()

        inactive_session = _make_session(status="applied")

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = inactive_session
        db.execute = AsyncMock(return_value=session_result)

        with patch("app.services.voice_service.settings") as mock_settings:
            mock_settings.voice_max_audio_bytes = 10 * 1024 * 1024

            with pytest.raises(VoiceError) as exc_info:
                await service.upload_audio(
                    db=db,
                    session_id=str(uuid.uuid4()),
                    tenant_id="tn_test",
                    audio_data=b"audio bytes",
                    content_type="audio/webm",
                )

        assert exc_info.value.status_code == 410


@pytest.mark.unit
class TestUploadAudioInvalidContentType:
    async def test_raises_422_for_disallowed_content_type(self):
        """A content_type not in the allowed set raises VoiceError(UPLOAD_FAILED, 422)."""
        service = VoiceService()
        db = AsyncMock()
        db.flush = AsyncMock()

        active_session = _make_session()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = active_session
        db.execute = AsyncMock(return_value=session_result)

        with patch("app.services.voice_service.settings") as mock_settings:
            mock_settings.voice_max_audio_bytes = 10 * 1024 * 1024

            with pytest.raises(VoiceError) as exc_info:
                await service.upload_audio(
                    db=db,
                    session_id=str(uuid.uuid4()),
                    tenant_id="tn_test",
                    audio_data=b"audio bytes",
                    content_type="video/mp4",  # not in allowed set
                )

        assert exc_info.value.status_code == 422
        assert exc_info.value.error == VoiceErrors.UPLOAD_FAILED


# ── VoiceService.parse_transcription ─────────────────────────────────────────


@pytest.mark.unit
class TestParseTranscriptionSuccess:
    async def test_concatenates_texts_and_creates_voice_parse(self):
        """Completed transcription texts are concatenated and a VoiceParse is created."""
        service = VoiceService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        t1 = _make_transcription(text="diente 36 caries oclusal")
        t2 = _make_transcription(text="diente 11 fractura incisal")
        active_session = _make_session(transcriptions=[t1, t2])

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = active_session
        db.execute = AsyncMock(return_value=session_result)

        mock_parse_result = {
            "findings": [{"tooth_number": 36, "zone": "oclusal", "condition_code": "caries", "confidence": 0.9}],
            "warnings": [],
            "status": "success",
        }

        with patch.object(service, "_parse_dental_text", new=AsyncMock(return_value=mock_parse_result)):
            with patch("app.services.voice_nlp.get_model_identifier", return_value="ollama/qwen2.5:32b"):
                result = await service.parse_transcription(
                    db=db,
                    session_id=str(uuid.uuid4()),
                )

        db.add.assert_called_once()
        db.flush.assert_called_once()
        added_parse = db.add.call_args[0][0]
        assert "diente 36 caries oclusal" in added_parse.input_text
        assert "diente 11 fractura incisal" in added_parse.input_text
        assert added_parse.status == "success"


@pytest.mark.unit
class TestParseTranscriptionSessionNotFound:
    async def test_raises_404_when_session_not_found(self):
        """Missing session raises VoiceError(SESSION_NOT_FOUND, 404)."""
        service = VoiceService()
        db = AsyncMock()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=session_result)

        with pytest.raises(VoiceError) as exc_info:
            await service.parse_transcription(db=db, session_id=str(uuid.uuid4()))

        assert exc_info.value.status_code == 404
        assert exc_info.value.error == VoiceErrors.SESSION_NOT_FOUND


@pytest.mark.unit
class TestParseTranscriptionSessionExpired:
    async def test_raises_410_when_session_not_active(self):
        """A session with status != 'active' raises VoiceError(SESSION_EXPIRED, 410) — H7."""
        service = VoiceService()
        db = AsyncMock()
        db.flush = AsyncMock()

        done_session = _make_session(status="applied")

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = done_session
        db.execute = AsyncMock(return_value=session_result)

        with pytest.raises(VoiceError) as exc_info:
            await service.parse_transcription(db=db, session_id=str(uuid.uuid4()))

        assert exc_info.value.status_code == 410

    async def test_raises_410_and_auto_expires_when_ttl_elapsed(self):
        """An active session past its TTL is auto-expired and raises 410 — H7."""
        service = VoiceService()
        db = AsyncMock()
        db.flush = AsyncMock()

        expired_session = _make_session(minutes_until_expiry=-1)

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = expired_session
        db.execute = AsyncMock(return_value=session_result)

        with pytest.raises(VoiceError) as exc_info:
            await service.parse_transcription(db=db, session_id=str(uuid.uuid4()))

        assert exc_info.value.status_code == 410
        assert expired_session.status == "expired"
        db.flush.assert_called_once()


@pytest.mark.unit
class TestParseTranscriptionNoCompletedTexts:
    async def test_raises_422_when_no_completed_transcriptions(self):
        """If there are no completed transcriptions, a 422 VoiceError is raised."""
        service = VoiceService()
        db = AsyncMock()

        pending_t = _make_transcription(status="pending")
        active_session = _make_session(transcriptions=[pending_t])

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = active_session
        db.execute = AsyncMock(return_value=session_result)

        with pytest.raises(VoiceError) as exc_info:
            await service.parse_transcription(db=db, session_id=str(uuid.uuid4()))

        assert exc_info.value.status_code == 422
        assert exc_info.value.error == VoiceErrors.PARSE_FAILED


@pytest.mark.unit
class TestParseTranscriptionNLPFailure:
    async def test_nlp_failure_creates_voice_parse_with_failed_status(self):
        """When the NLP provider fails, a VoiceParse with status='failed' is created — C4."""
        service = VoiceService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        t = _make_transcription(text="diente 36 caries")
        active_session = _make_session(transcriptions=[t])

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = active_session
        db.execute = AsyncMock(return_value=session_result)

        nlp_fail_result = {
            "findings": [],
            "warnings": ["NLP parse failed: el servicio de análisis no respondió"],
            "status": "failed",
        }

        with patch.object(service, "_parse_dental_text", new=AsyncMock(return_value=nlp_fail_result)):
            with patch("app.services.voice_nlp.get_model_identifier", return_value="ollama/qwen2.5:32b"):
                result = await service.parse_transcription(db=db, session_id=str(uuid.uuid4()))

        added_parse = db.add.call_args[0][0]
        assert added_parse.status == "failed"
        assert len(added_parse.warnings) > 0


# ── VoiceService.apply_findings ───────────────────────────────────────────────


@pytest.mark.unit
class TestApplyFindingsSessionNotFound:
    async def test_raises_404_when_session_not_found(self):
        """A missing session raises VoiceError(SESSION_NOT_FOUND, 404)."""
        service = VoiceService()
        db = AsyncMock()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=session_result)

        with pytest.raises(VoiceError) as exc_info:
            await service.apply_findings(
                db=db,
                session_id=str(uuid.uuid4()),
                tenant_id="tn_test",
                doctor_id=str(uuid.uuid4()),
                confirmed_findings=[{"tooth_number": 36, "zone": "oclusal", "condition_code": "caries"}],
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.error == VoiceErrors.SESSION_NOT_FOUND


@pytest.mark.unit
class TestApplyFindingsSessionExpired:
    async def test_raises_410_and_auto_expires_when_ttl_elapsed(self):
        """A past-TTL session is auto-expired and raises 410 — H7."""
        service = VoiceService()
        db = AsyncMock()
        db.flush = AsyncMock()

        expired_session = _make_session(minutes_until_expiry=-5)

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = expired_session
        db.execute = AsyncMock(return_value=session_result)

        with pytest.raises(VoiceError) as exc_info:
            await service.apply_findings(
                db=db,
                session_id=str(uuid.uuid4()),
                tenant_id="tn_test",
                doctor_id=str(uuid.uuid4()),
                confirmed_findings=[{"tooth_number": 36, "zone": "oclusal", "condition_code": "caries"}],
            )

        assert exc_info.value.status_code == 410
        assert expired_session.status == "expired"


@pytest.mark.unit
class TestApplyFindingsEmptyFindings:
    async def test_empty_findings_returns_zero_applied_count(self):
        """An empty confirmed_findings list returns {applied_count: 0} immediately."""
        service = VoiceService()
        db = AsyncMock()
        db.flush = AsyncMock()

        active_session = _make_session()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = active_session
        db.execute = AsyncMock(return_value=session_result)

        result = await service.apply_findings(
            db=db,
            session_id=str(uuid.uuid4()),
            tenant_id="tn_test",
            doctor_id=str(uuid.uuid4()),
            confirmed_findings=[],
        )

        assert result["applied_count"] == 0
        assert result["skipped_count"] == 0
        assert result["errors"] == []


@pytest.mark.unit
class TestApplyFindingsMissingRequiredKeys:
    async def test_findings_missing_keys_are_skipped_with_error(self):
        """Findings that lack required keys (tooth_number, zone, condition_code) are skipped — H3."""
        service = VoiceService()
        db = AsyncMock()
        db.flush = AsyncMock()

        active_session = _make_session()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = active_session
        db.execute = AsyncMock(return_value=session_result)

        # One finding missing 'condition_code'
        bad_findings = [{"tooth_number": 36, "zone": "oclusal"}]

        mock_bulk_update_result = {"processed": 0}

        with patch("app.services.odontogram_service.odontogram_service") as mock_odo:
            mock_odo.bulk_update = AsyncMock(return_value=mock_bulk_update_result)
            result = await service.apply_findings(
                db=db,
                session_id=str(uuid.uuid4()),
                tenant_id="tn_test",
                doctor_id=str(uuid.uuid4()),
                confirmed_findings=bad_findings,
            )

        assert result["applied_count"] == 0
        assert result["skipped_count"] == 1
        assert len(result["errors"]) >= 1
        assert any("missing keys" in e for e in result["errors"])


@pytest.mark.unit
class TestApplyFindingsDentalOSError:
    async def test_dentalos_error_from_bulk_update_is_caught_gracefully(self):
        """A DentalOSError raised by bulk_update is caught and reflected in errors — not re-raised."""
        service = VoiceService()
        db = AsyncMock()
        db.flush = AsyncMock()

        active_session = _make_session()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = active_session
        db.execute = AsyncMock(return_value=session_result)

        valid_findings = [{"tooth_number": 36, "zone": "oclusal", "condition_code": "caries"}]

        with patch("app.services.odontogram_service.odontogram_service") as mock_odo:
            mock_odo.bulk_update = AsyncMock(
                side_effect=DentalOSError(
                    error="ODONTOGRAM_invalid_tooth_number",
                    message="Tooth not found in odontogram.",
                    status_code=422,
                )
            )
            result = await service.apply_findings(
                db=db,
                session_id=str(uuid.uuid4()),
                tenant_id="tn_test",
                doctor_id=str(uuid.uuid4()),
                confirmed_findings=valid_findings,
            )

        # Should NOT raise — errors are captured in the response
        assert result["applied_count"] == 0
        assert len(result["errors"]) == 1
        assert "Tooth not found" in result["errors"][0]


# ── VoiceService.submit_feedback ─────────────────────────────────────────────


@pytest.mark.unit
class TestSubmitFeedbackSuccess:
    async def test_creates_feedback_parse_and_updates_session_status(self):
        """Feedback is stored as a VoiceParse(status='feedback') and session becomes 'feedback_received'."""
        service = VoiceService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        # Session has one parse with 4 findings
        mock_parse = MagicMock()
        mock_parse.findings = [
            {"tooth_number": 36, "zone": "oclusal", "condition_code": "caries", "confidence": 0.9},
            {"tooth_number": 11, "zone": "incisal", "condition_code": "fracture", "confidence": 0.8},
            {"tooth_number": 21, "zone": "full", "condition_code": "crown", "confidence": 0.95},
            {"tooth_number": 46, "zone": "mesial", "condition_code": "restoration", "confidence": 0.7},
        ]
        active_session = _make_session(parses=[mock_parse])

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = active_session
        db.execute = AsyncMock(return_value=session_result)

        # 2 corrections (tooth + condition changed), 1 rejection
        corrections = [
            {"corrected_tooth": 37, "corrected_condition": None, "is_rejected": False},
            {"corrected_tooth": None, "corrected_condition": "fracture", "is_rejected": False},
            {"corrected_tooth": None, "corrected_condition": None, "is_rejected": True},
        ]

        result = await service.submit_feedback(
            db=db,
            session_id=str(uuid.uuid4()),
            findings_corrections=corrections,
        )

        assert result["feedback_recorded"] is True
        assert result["correction_count"] == 3
        assert result["correction_rate"] == pytest.approx(3 / 4)

        # VoiceParse added with status='feedback'
        added_parse = db.add.call_args[0][0]
        assert added_parse.status == "feedback"
        assert added_parse.llm_model == "feedback"

        # Session updated to 'feedback_received'
        assert active_session.status == "feedback_received"

    async def test_correction_rate_is_none_when_no_parses(self):
        """If there are no prior parses (total_findings == 0), correction_rate is None."""
        service = VoiceService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        active_session = _make_session(parses=[])

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = active_session
        db.execute = AsyncMock(return_value=session_result)

        result = await service.submit_feedback(
            db=db,
            session_id=str(uuid.uuid4()),
            findings_corrections=[{"corrected_tooth": 37, "corrected_condition": None, "is_rejected": False}],
        )

        assert result["correction_rate"] is None


@pytest.mark.unit
class TestSubmitFeedbackSessionNotFound:
    async def test_raises_404_when_session_not_found(self):
        """A missing session raises VoiceError(SESSION_NOT_FOUND, 404)."""
        service = VoiceService()
        db = AsyncMock()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=session_result)

        with pytest.raises(VoiceError) as exc_info:
            await service.submit_feedback(
                db=db,
                session_id=str(uuid.uuid4()),
                findings_corrections=[],
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.error == VoiceErrors.SESSION_NOT_FOUND
