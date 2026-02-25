"""Unit tests for the AuditLog SQLAlchemy model.

These tests verify that the model can be instantiated with valid data and that
all expected columns/fields are present. No database connection is required —
we only test Python-side object construction and metadata inspection.
"""
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect as sa_inspect

from app.models.audit import AuditLog


@pytest.mark.unit
class TestAuditLogInstantiation:
    def test_minimal_instantiation(self):
        """AuditLog can be created with just the required fields."""
        log = AuditLog(
            action="create",
            resource_type="patient",
        )
        assert log.action == "create"
        assert log.resource_type == "patient"

    def test_full_instantiation(self):
        """AuditLog stores all provided field values correctly."""
        user_id = uuid.uuid4()
        log = AuditLog(
            user_id=user_id,
            action="update",
            resource_type="odontogram",
            resource_id=str(uuid.uuid4()),
            changes={"tooth_number": {"old": "11", "new": "21"}},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        assert log.user_id == user_id
        assert log.action == "update"
        assert log.resource_type == "odontogram"
        assert log.changes["tooth_number"]["old"] == "11"
        assert log.ip_address == "192.168.1.1"
        assert log.user_agent == "Mozilla/5.0"

    def test_nullable_fields_default_to_none(self):
        """Optional fields are None when not provided."""
        log = AuditLog(action="login", resource_type="user")
        assert log.user_id is None
        assert log.resource_id is None
        assert log.changes is None
        assert log.ip_address is None
        assert log.user_agent is None

    def test_action_values_accepted(self):
        """Standard audit action strings are valid."""
        for action in ("create", "update", "delete", "login", "logout"):
            log = AuditLog(action=action, resource_type="user")
            assert log.action == action

    def test_resource_type_values_accepted(self):
        """Common resource type strings are valid."""
        for resource in ("user", "patient", "odontogram", "appointment", "invoice"):
            log = AuditLog(action="create", resource_type=resource)
            assert log.resource_type == resource

    def test_changes_accepts_nested_dict(self):
        """The JSONB changes field accepts arbitrarily nested change dicts."""
        changes = {
            "email": {"old": "old@test.co", "new": "new@test.co"},
            "name": {"old": "Dr A", "new": "Dr B"},
        }
        log = AuditLog(action="update", resource_type="user", changes=changes)
        assert log.changes["email"]["new"] == "new@test.co"

    def test_uuid_as_resource_id_string(self):
        resource_id = str(uuid.uuid4())
        log = AuditLog(action="delete", resource_type="patient", resource_id=resource_id)
        assert log.resource_id == resource_id


@pytest.mark.unit
class TestAuditLogTableMetadata:
    def test_table_name(self):
        assert AuditLog.__tablename__ == "audit_logs"

    def test_expected_columns_exist(self):
        """All required columns are declared on the model."""
        mapper = sa_inspect(AuditLog)
        column_names = {col.key for col in mapper.mapper.column_attrs}

        expected = {
            "id",
            "user_id",
            "action",
            "resource_type",
            "resource_id",
            "changes",
            "ip_address",
            "user_agent",
            "created_at",
        }
        for col in expected:
            assert col in column_names, f"Expected column {col!r} not found on AuditLog"

    def test_no_updated_at_column(self):
        """AuditLog must not have updated_at — logs are immutable."""
        mapper = sa_inspect(AuditLog)
        column_names = {col.key for col in mapper.mapper.column_attrs}
        assert "updated_at" not in column_names

    def test_no_is_active_column(self):
        """AuditLog must not have is_active — logs are never soft-deleted."""
        mapper = sa_inspect(AuditLog)
        column_names = {col.key for col in mapper.mapper.column_attrs}
        assert "is_active" not in column_names

    def test_table_indexes_declared(self):
        """Expected performance indexes are defined on the table."""
        index_names = {idx.name for idx in AuditLog.__table__.indexes}
        assert "idx_audit_logs_user_id" in index_names
        assert "idx_audit_logs_resource" in index_names
        assert "idx_audit_logs_created_at" in index_names

    def test_id_is_primary_key(self):
        primary_keys = {col.key for col in sa_inspect(AuditLog).mapper.primary_key}
        assert "id" in primary_keys
