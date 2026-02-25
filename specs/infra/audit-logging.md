# Audit Logging Spec

> **Spec ID:** I-11 | **Status:** Draft | **Last Updated:** 2026-02-24

---

## 1. Overview

DentalOS maintains an immutable audit trail for all clinically significant operations. This is required for healthcare compliance in LATAM -- specifically Colombia's RDA regulations (Resolucion 1995 de 1999, Resolucion 839 de 2017) and data protection law (Ley 1581 de 2012). Every access to patient data, every clinical record modification, and every administrative action must be traceable to a user, timestamp, and IP address. Records are append-only, tamper-proof at the database level, and retained for a minimum of 15 years.

**Stack:** Python 3.12 + FastAPI + PostgreSQL (per-tenant schema) + RabbitMQ (async writes)

**Dependencies:** I-01 (multi-tenancy.md), I-04 (database-architecture.md), I-06 (background-processing.md)

---

## 2. What Gets Logged

**Clinical data (ALL read/write):** `odontogram` (read/create/update), `clinical_record` (read/create/update), `diagnosis` (read/create/update/delete), `prescription` (read/create), `treatment_plan` (read/create/update/delete).

**Patient data:** `patient` (create/update/delete), `patient_document` (create/read/delete).

**Consent:** `consent` (create/read/update) -- signing, revocation, viewing.

**Auth events:** `auth_session` (login/logout), `auth_failed_login` (create), `auth_password_change` (update), `auth_password_reset` (update). Passwords are NEVER logged -- only the event.

**Admin actions:** `user` (create/update/delete), `user_role` (update), `user_invite` (create), `tenant_settings` (update).

**Data exports:** `data_export` (export -- patient records, clinical summaries), `rips_generation` (create -- Colombia RIPS), `invoice_export` (export).

---

## 3. Audit Log Schema

Each tenant schema has its own `audit_logs` table (not shared), guaranteeing tenant isolation.

```sql
CREATE TABLE audit_logs (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(50)     NOT NULL,
    user_id         UUID            NOT NULL,
    user_role       VARCHAR(30)     NOT NULL,
    action          VARCHAR(10)     NOT NULL
        CHECK (action IN ('create','read','update','delete','export','login','logout')),
    resource_type   VARCHAR(60)     NOT NULL,
    resource_id     UUID,
    old_value       JSONB,          -- previous state (update/delete only)
    new_value       JSONB,          -- new state (create/update only)
    changed_fields  TEXT[],         -- field names that changed (update only)
    ip_address      INET            NOT NULL,
    user_agent      TEXT,
    session_id      UUID,
    correlation_id  VARCHAR(100),
    metadata        JSONB           DEFAULT '{}',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT audit_no_future CHECK (created_at <= NOW() + INTERVAL '1 minute')
);

CREATE INDEX idx_audit_user      ON audit_logs (user_id, created_at DESC);
CREATE INDEX idx_audit_resource  ON audit_logs (resource_type, resource_id, created_at DESC);
CREATE INDEX idx_audit_action    ON audit_logs (action, created_at DESC);
CREATE INDEX idx_audit_timestamp ON audit_logs (created_at DESC);
CREATE INDEX idx_audit_clinical  ON audit_logs (resource_type, created_at DESC)
    WHERE resource_type IN ('odontogram','clinical_record','diagnosis',
                            'prescription','treatment_plan','consent');
```

Append-only. No UPDATE or DELETE permitted (see Section 6).

---

## 4. What NEVER Gets Logged

| Excluded | Reason |
|----------|--------|
| Raw passwords / hashes | Security. Only "password changed" event is logged. |
| Full PHI in plaintext | Reference by resource ID. Diffs stored, not full records. |
| Credit card numbers | PCI compliance. Only billing metadata (amount, status). |
| JWT / refresh tokens | Security. Only `session_id` (JTI) for correlation. |

`old_value`/`new_value` capped at 50 KB. Larger payloads replaced with `{"_truncated": true, "_fields": [...]}`.

---

## 5. Implementation

### 5.1 Decorator `@audited()` for FastAPI Route Handlers

```python
# app/audit/decorator.py
import functools
from fastapi import Request

def audited(action: str, resource_type: str, resource_id_param: str = None,
            capture_old_value: bool = False):
    """Auto-logs audit entry after successful route execution."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get("request") or _find_request(args)
            user = request.state.user
            resource_id = kwargs.get(resource_id_param) if resource_id_param else None
            old_value = (await _fetch_current_state(request, resource_type, resource_id)
                         if capture_old_value and resource_id else None)
            result = await func(*args, **kwargs)
            new_value = result.model_dump(mode="json") if hasattr(result, "model_dump") else None
            changed_fields = ([k for k in new_value if k in old_value and old_value[k] != new_value[k]]
                              if action == "update" and old_value and new_value else None)
            await request.state.audit_service.log(
                tenant_id=request.state.tenant_id, user_id=str(user.id),
                user_role=user.role, action=action, resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                old_value=old_value, new_value=new_value, changed_fields=changed_fields,
                ip_address=_get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                correlation_id=request.headers.get("x-request-id"),
            )
            return result
        return wrapper
    return decorator

# Usage:
@router.put("/patients/{patient_id}")
@audited(action="update", resource_type="patient",
         resource_id_param="patient_id", capture_old_value=True)
async def update_patient(patient_id: str, body: PatientUpdate, request: Request):
    return await patient_service.update(patient_id, body)
```

### 5.2 SQLAlchemy Event Listener for Change Detection

```python
# app/audit/sqlalchemy_listener.py
from sqlalchemy import event, inspect

@event.listens_for(Session, "after_flush")
def capture_changes(session, flush_context):
    for obj in session.dirty:
        if not hasattr(obj, "__audit_tracked__"): continue
        old, new, changed = {}, {}, []
        for attr in inspect(type(obj)).column_attrs:
            history = inspect(obj).attrs[attr.key].history
            if history.has_changes():
                old[attr.key] = history.deleted[0] if history.deleted else None
                new[attr.key] = history.added[0] if history.added else None
                changed.append(attr.key)
        if changed:
            session.info.setdefault("_audit_changes", []).append({
                "resource_type": obj.__tablename__, "resource_id": str(obj.id),
                "old_value": old, "new_value": new, "changed_fields": changed,
            })
```

### 5.3 Async Write via RabbitMQ

```python
# app/audit/service.py
class AuditService:
    def __init__(self, publisher: JobPublisher):
        self._publisher = publisher

    async def log(self, tenant_id, user_id, user_role, action, resource_type, **kw):
        entry = {"tenant_id": tenant_id, "user_id": user_id, "user_role": user_role,
                 "action": action, "resource_type": resource_type, **kw}
        return await self._publisher.publish(
            queue="maintenance", job_type="audit.write", tenant_id=tenant_id,
            payload=entry, priority=4, max_retries=5,
        )
```

Worker consumes `audit.write` and inserts into `tenant_{id}.audit_logs`. If RabbitMQ is down, entries buffer to `/var/log/dentalos/audit-buffer.jsonl` and replay on recovery.

---

## 6. Immutability Enforcement

### PostgreSQL Triggers (included in Alembic migration)

```sql
CREATE OR REPLACE FUNCTION prevent_audit_update() RETURNS TRIGGER AS $$
BEGIN RAISE EXCEPTION 'audit_logs: UPDATE operations are forbidden'; END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_audit_no_update BEFORE UPDATE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_update();

CREATE OR REPLACE FUNCTION prevent_audit_delete() RETURNS TRIGGER AS $$
BEGIN
    IF current_setting('app.audit_archival_mode', true) = 'true' THEN RETURN OLD; END IF;
    RAISE EXCEPTION 'audit_logs: DELETE operations are forbidden';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_audit_no_delete BEFORE DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_delete();
```

### Application-Level
- `AuditLog` model has no `update()` or `delete()` methods.
- No API endpoint exists to modify or delete audit records.
- Alembic migration includes both triggers automatically.

---

## 7. Retention Policy

**Minimum: 15 years** (Colombia Resolucion 1995, Articulo 15). Active table holds 2 years; older records archived to gzipped JSONL in S3-compatible storage (Hetzner Object Storage, bucket `dentalos-audit-archive/{tenant_id}/`).

| Country | Regulation | Retention |
|---------|-----------|-----------|
| Colombia | Resolucion 1995 de 1999 | 15 years |
| Mexico | NOM-004-SSA3-2012 | 5 years |
| Chile | Ley 20.584 | 15 years |
| Argentina | Ley 26.529 | 10 years |
| Peru | Ley 30024 | 20 years |

**Storage per tenant:** Small clinic (~200 entries/day) = ~600 MB/year. Medium (~800/day) = ~2.4 GB/year. Large (~3,000/day) = ~9 GB/year. Compressed archives reduce by ~80%.

---

## 8. Query Patterns

**"All access to patient X's records"** (compliance audit):
```sql
SELECT user_id, user_role, action, resource_type, created_at, ip_address
FROM audit_logs
WHERE resource_type IN ('patient','odontogram','clinical_record','treatment_plan','prescription','consent')
  AND (resource_id = :patient_id OR metadata->>'patient_id' = :patient_id_str)
ORDER BY created_at DESC LIMIT 100 OFFSET :offset;
```

**"All actions by user Y in date range"** (security investigation):
```sql
SELECT action, resource_type, resource_id, created_at, ip_address FROM audit_logs
WHERE user_id = :user_id AND created_at BETWEEN :start AND :end
ORDER BY created_at DESC LIMIT 100 OFFSET :offset;
```

**"All login failures in last 24h"** (security monitoring):
```sql
SELECT user_id, ip_address, user_agent, created_at FROM audit_logs
WHERE resource_type = 'auth_failed_login' AND created_at >= NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

---

## 9. Performance

- **Async writes:** RabbitMQ `audit.write` job (priority 4). API response time unaffected. Worker batch-inserts groups of 50. Dead-lettered audit messages trigger immediate alerts.
- **Partitioning (Enterprise tenants):** `PARTITION BY RANGE (created_at)` with monthly partitions (`audit_logs_2026_01`, `audit_logs_2026_02`, ...). Created automatically by maintenance job. Old partitions (> 2 years) archived and detached. Free/Pro tenants use unpartitioned tables.
- **Query timeout:** 30 seconds max to prevent runaway scans.

---

## 10. Compliance

**Colombia Resolucion 1995/839:** Clinical records must be complete, sequential, with creator identification. Satisfied by `user_id`, `user_role`, `created_at`. All access and modifications traceable via `action` field including `read`. 15-year retention enforced.

**Colombia Ley 1581 (Habeas Data):** Patients can request who accessed their data. The "all access to patient X" query (Section 8) enables this right.

**Mexico NOM-024-SSA3-2012:** EHR integrity and traceability required. Immutability triggers (Section 6) and audit trail satisfy this. 5-year minimum retention.

**General:** Complete chain of custody for every clinical data point -- who created, viewed, modified, when, from where. Export functionality (CSV, JSON, PDF) for regulatory inspections.

---

## 11. Testing

```python
# tests/test_audit.py

async def test_patient_update_creates_audit_entry(client, db_session, test_patient):
    response = await client.put(f"/api/v1/patients/{test_patient.id}", json={"first_name": "Updated"})
    assert response.status_code == 200
    await process_pending_audit_messages()
    audit = await db_session.execute(
        select(AuditLog).where(AuditLog.resource_type == "patient",
                                AuditLog.resource_id == test_patient.id, AuditLog.action == "update"))
    entry = audit.scalar_one()
    assert entry.changed_fields == ["first_name"]
    assert entry.new_value["first_name"] == "Updated"

async def test_audit_immutability(db_session):
    entry = await create_audit_entry(db_session, action="read", resource_type="patient")
    with pytest.raises(Exception, match="UPDATE operations are forbidden"):
        await db_session.execute(update(AuditLog).where(AuditLog.id == entry.id).values(action="delete"))
    with pytest.raises(Exception, match="DELETE operations are forbidden"):
        await db_session.execute(delete(AuditLog).where(AuditLog.id == entry.id))

async def test_clinical_read_is_audited(client, test_patient):
    response = await client.get(f"/api/v1/patients/{test_patient.id}/odontogram")
    assert response.status_code == 200
    await process_pending_audit_messages()
    entries = await get_audit_entries(resource_type="odontogram", resource_id=test_patient.id)
    assert len(entries) >= 1 and entries[0].action == "read"
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
| 2.0 | 2026-02-24 | Full rewrite: regulatory context, detailed logging rules, immutability triggers, async RabbitMQ writes, compliance mapping (Colombia/Mexico), retention policy, query patterns, testing |
