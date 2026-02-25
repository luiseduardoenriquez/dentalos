"""Unit tests for the QueueMessage Pydantic schema.

Validates default values, field constraints, and JSON serialization behavior
for the standard RabbitMQ message envelope.
"""
import json
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.queue import QueueMessage


def _minimal(**overrides) -> dict:
    """Minimal valid payload for QueueMessage."""
    base = {
        "tenant_id": "tn_abc123",
        "job_type": "email.send",
    }
    base.update(overrides)
    return base


@pytest.mark.unit
class TestQueueMessageDefaults:
    def test_message_id_auto_generated(self):
        msg = QueueMessage(**_minimal())
        assert msg.message_id
        # Must be a parseable UUID
        uuid.UUID(msg.message_id)

    def test_each_instance_gets_unique_message_id(self):
        msg1 = QueueMessage(**_minimal())
        msg2 = QueueMessage(**_minimal())
        assert msg1.message_id != msg2.message_id

    def test_default_priority_is_five(self):
        msg = QueueMessage(**_minimal())
        assert msg.priority == 5

    def test_default_retry_count_is_zero(self):
        msg = QueueMessage(**_minimal())
        assert msg.retry_count == 0

    def test_default_max_retries_is_three(self):
        msg = QueueMessage(**_minimal())
        assert msg.max_retries == 3

    def test_default_payload_is_empty_dict(self):
        msg = QueueMessage(**_minimal())
        assert msg.payload == {}

    def test_created_at_is_utc_aware(self):
        from datetime import timezone

        msg = QueueMessage(**_minimal())
        assert msg.created_at.tzinfo is not None
        assert msg.created_at.utcoffset().total_seconds() == 0

    def test_required_fields_stored(self):
        msg = QueueMessage(tenant_id="tn_xyz", job_type="clinical.pdf")
        assert msg.tenant_id == "tn_xyz"
        assert msg.job_type == "clinical.pdf"


@pytest.mark.unit
class TestQueueMessageValidation:
    def test_priority_minimum_one(self):
        with pytest.raises(ValidationError):
            QueueMessage(**_minimal(priority=0))

    def test_priority_maximum_ten(self):
        with pytest.raises(ValidationError):
            QueueMessage(**_minimal(priority=11))

    def test_priority_boundary_one_accepted(self):
        msg = QueueMessage(**_minimal(priority=1))
        assert msg.priority == 1

    def test_priority_boundary_ten_accepted(self):
        msg = QueueMessage(**_minimal(priority=10))
        assert msg.priority == 10

    def test_retry_count_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            QueueMessage(**_minimal(retry_count=-1))

    def test_retry_count_zero_accepted(self):
        msg = QueueMessage(**_minimal(retry_count=0))
        assert msg.retry_count == 0

    def test_max_retries_zero_accepted(self):
        """max_retries=0 means no retries — valid for fire-and-forget jobs."""
        msg = QueueMessage(**_minimal(max_retries=0))
        assert msg.max_retries == 0

    def test_missing_tenant_id_raises(self):
        with pytest.raises(ValidationError):
            QueueMessage(job_type="email.send")

    def test_missing_job_type_raises(self):
        with pytest.raises(ValidationError):
            QueueMessage(tenant_id="tn_abc")

    def test_payload_accepts_nested_dict(self):
        payload = {"to": "user@test.co", "template": "welcome", "vars": {"name": "Dr. Test"}}
        msg = QueueMessage(**_minimal(payload=payload))
        assert msg.payload["vars"]["name"] == "Dr. Test"


@pytest.mark.unit
class TestQueueMessageSerialization:
    def test_model_dump_produces_dict(self):
        msg = QueueMessage(**_minimal())
        data = msg.model_dump()
        assert isinstance(data, dict)
        assert "message_id" in data
        assert "tenant_id" in data
        assert "job_type" in data

    def test_model_dump_json_is_valid_json(self):
        msg = QueueMessage(**_minimal())
        raw = msg.model_dump_json()
        parsed = json.loads(raw)
        assert parsed["tenant_id"] == "tn_abc123"
        assert parsed["job_type"] == "email.send"
        assert parsed["priority"] == 5

    def test_roundtrip_from_dict(self):
        """Deserializing a serialized message produces an equal model."""
        original = QueueMessage(**_minimal(priority=8, retry_count=2))
        data = original.model_dump()
        restored = QueueMessage.model_validate(data)
        assert restored.message_id == original.message_id
        assert restored.priority == 8
        assert restored.retry_count == 2
