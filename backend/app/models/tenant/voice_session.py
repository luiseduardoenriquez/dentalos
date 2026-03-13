"""Voice session models — live in each tenant schema.

Three tables:
  - VoiceSession:       a single voice-to-odontogram/evolution session per doctor+patient
  - VoiceTranscription: Whisper chunk transcription record with S3 audio key
  - VoiceParse:         Claude parse result mapping transcription text to dental findings
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class VoiceSession(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A voice dictation session used to update odontogram or evolution notes.

    Context determines which downstream models are updated when parses are applied:
      - odontogram:  findings are applied as OdontogramCondition rows
      - evolution:   findings are appended to a ClinicalRecord evolution note
      - examination: findings feed the examination section of a ClinicalRecord

    Status transitions:
      active → applied (findings committed to target model)
      active → expired (TTL elapsed without commit)

    Sessions expire at expires_at; the maintenance worker cleans up expired
    sessions and their child rows after a retention period.

    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "voice_sessions"
    __table_args__ = (
        CheckConstraint(
            "context IN ('odontogram', 'evolution', 'examination')",
            name="chk_voice_sessions_context",
        ),
        CheckConstraint(
            "status IN ('active', 'applied', 'expired', 'feedback_received')",
            name="chk_voice_sessions_status",
        ),
        Index("idx_voice_sessions_doctor", "doctor_id"),
        Index("idx_voice_sessions_patient", "patient_id"),
    )

    # Ownership
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Session type
    context: Mapped[str] = mapped_column(
        String(20), nullable=False, default="odontogram"
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Expiry — set at creation (e.g. now + 30 minutes)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    transcriptions: Mapped[list["VoiceTranscription"]] = relationship(
        back_populates="session",
        lazy="selectin",
        order_by="VoiceTranscription.chunk_index",
    )
    parses: Mapped[list["VoiceParse"]] = relationship(
        back_populates="session",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<VoiceSession doctor={self.doctor_id} "
            f"patient={self.patient_id} context={self.context} status={self.status}>"
        )


class VoiceTranscription(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A Whisper transcription result for a single audio chunk.

    Audio is uploaded to S3 and the key stored here; the text is populated
    once the Whisper worker finishes processing.

    chunk_index tracks ordering when a session has multiple audio chunks
    (e.g. doctor pauses and resumes dictation).

    estimated_cost_usd is the Whisper API cost in USD to 6 decimal places
    (micro-dollars precision) for billing attribution.
    """

    __tablename__ = "voice_transcriptions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="chk_voice_transcriptions_status",
        ),
        Index("idx_voice_transcriptions_session", "session_id"),
    )

    # Parent session
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voice_sessions.id"),
        nullable=False,
    )

    # Chunk ordering
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Idempotency — client-generated key to prevent duplicate uploads on retry
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )

    # Audio storage
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)

    # Processing state
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # Transcription output (populated on completion)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Cost tracking (USD, 6 decimal precision)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )

    # Relationship
    session: Mapped["VoiceSession"] = relationship(back_populates="transcriptions")

    def __repr__(self) -> str:
        return (
            f"<VoiceTranscription session={self.session_id} "
            f"chunk={self.chunk_index} status={self.status}>"
        )


class VoiceParse(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A Claude LLM parse of assembled transcription text into dental findings.

    findings is a JSONB array of structured finding objects ready to be
    applied to the target model (odontogram conditions, evolution fields, etc.):
        [{"tooth": 16, "zone": "oclusal", "condition": "caries", "severity": "mild"}, ...]

    corrections is a JSONB array of auto-corrections the LLM applied
    (e.g. "dente" → tooth number normalisation).

    filtered_speech is a JSONB array of non-clinical utterances that were
    stripped before parsing (filler words, side conversations).

    warnings is a JSONB array of ambiguous or unresolvable phrases the
    doctor should review before committing.

    llm_cost_usd is the Claude API cost in USD to 6 decimal places.
    """

    __tablename__ = "voice_parses"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'partial', 'feedback', 'failed')",
            name="chk_voice_parses_status",
        ),
        Index("idx_voice_parses_session", "session_id"),
    )

    # Parent session
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voice_sessions.id"),
        nullable=False,
    )

    # Input
    input_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Parse outputs
    findings: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )
    corrections: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )
    filtered_speech: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )
    warnings: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )

    # LLM metadata
    llm_model: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)

    # Parse result quality
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")

    # Relationship
    session: Mapped["VoiceSession"] = relationship(back_populates="parses")

    def __repr__(self) -> str:
        return (
            f"<VoiceParse session={self.session_id} "
            f"model={self.llm_model} status={self.status}>"
        )
