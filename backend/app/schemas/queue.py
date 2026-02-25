"""Queue message envelope schemas."""
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class QueueMessage(BaseModel):
    """Standard message envelope for all RabbitMQ messages."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    job_type: str
    payload: dict = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
