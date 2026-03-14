"""Pydantic schemas for the offline sync API."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ─── Delta Sync ───────────────────────────────────────────────────────────────


class SyncDeltaRequest(BaseModel):
    """Query parameters for delta sync."""

    since: datetime = Field(..., description="ISO 8601 timestamp — return records modified after this")
    resources: list[str] = Field(
        default=["patients", "appointments", "odontogram", "clinical_records"],
        description="Which resources to include in delta response",
    )


class SyncResourceDelta(BaseModel):
    """Delta data for a single resource type."""

    resource: str
    items: list[dict[str, Any]]
    total: int
    synced_at: datetime


class SyncDeltaResponse(BaseModel):
    """Response for delta sync — only modified records since the given timestamp."""

    deltas: list[SyncResourceDelta]
    server_time: datetime


# ─── Full Sync ────────────────────────────────────────────────────────────────


class SyncFullResponse(BaseModel):
    """Response for full sync — bounded dump of essential data."""

    patients: list[dict[str, Any]]
    appointments: list[dict[str, Any]]
    odontogram_states: list[dict[str, Any]]
    clinical_records: list[dict[str, Any]]
    server_time: datetime


# ─── Batch Write ──────────────────────────────────────────────────────────────


class SyncOperation(BaseModel):
    """A single write operation from the offline queue."""

    method: Literal["POST", "PUT", "DELETE"]
    resource: str = Field(..., description="Resource type: patients, appointments, clinical_records, odontogram")
    resource_id: str | None = Field(default=None, description="ID of the resource (for PUT/DELETE)")
    url: str = Field(..., description="Original API path (e.g., /patients, /appointments/uuid/confirm)")
    body: dict[str, Any] | None = Field(default=None, description="Request body")
    queued_at: datetime = Field(..., description="When this operation was queued on the client")


class SyncBatchRequest(BaseModel):
    """Batch of offline write operations to process."""

    operations: list[SyncOperation] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Ordered list of operations (max 50)",
    )


class SyncOperationResult(BaseModel):
    """Result for a single operation in the batch."""

    index: int
    status: Literal["success", "conflict", "error"]
    resource: str
    resource_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    server_data: dict[str, Any] | None = Field(
        default=None,
        description="Current server-side data (included on conflict for resolution)",
    )


class SyncBatchResponse(BaseModel):
    """Response for batch write processing."""

    results: list[SyncOperationResult]
    total: int
    succeeded: int
    conflicts: int
    errors: int
    server_time: datetime
