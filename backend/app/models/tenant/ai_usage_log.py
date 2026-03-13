"""AI usage log — tracks every AI API call across all features.

Records Claude, Whisper, and Ollama calls for usage metrics and billing.
Features that already have their own token columns (ai_treatment_suggestions,
voice_parses) also write here for a single source of truth.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, UUIDPrimaryKeyMixin


class AIUsageLog(UUIDPrimaryKeyMixin, TenantBase):
    """A single AI API call (Claude, Whisper, Ollama, etc.)."""

    __tablename__ = "ai_usage_logs"
    __table_args__ = (
        Index("idx_ai_usage_logs_doctor_created", "doctor_id", "created_at"),
        Index("idx_ai_usage_logs_feature", "feature"),
    )

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    feature: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # "voice_parse", "ai_report", "ai_treatment", "chatbot"
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<AIUsageLog doctor={self.doctor_id} "
            f"feature={self.feature} model={self.model}>"
        )
