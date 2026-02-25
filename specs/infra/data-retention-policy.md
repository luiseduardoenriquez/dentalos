# Data Retention Policy Spec

> **Spec ID:** I-12
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Data retention rules, deletion lifecycle, and automated cleanup policies for DentalOS. Clinical records retention follows country-specific healthcare regulations (Colombia: 15 years, Mexico: 5 years, Chile: 10 years). Patient right to erasure requests are handled within the constraints of clinical data retention mandates. Tenant lifecycle covers active → suspended → archived → deleted states.

**Domain:** infra / compliance

**Priority:** Critical

**Dependencies:** I-01 (multi-tenancy), I-11 (audit-logging), I-13 (hipaa-latam-compliance), I-16 (backup-DR), ADR-007 (country adapter)

---

## 1. Regulatory Retention Requirements

### Colombia

| Data Category | Regulation | Retention Period |
|--------------|-----------|-----------------|
| Historia Clínica (clinical records) | Ley 23/1981 + Resolución 1995/1999 | **20 years** from last entry (minimum) |
| Historia Clínica de menores | Resolución 1995/1999 | Until age 18 + 20 years |
| Radiografías, modelos, fotografías | Resolución 1995/1999 | **10 years** |
| Consentimientos informados | Resolución 1995/1999 | **10 years** |
| Facturación electrónica (DIAN) | Estatuto Tributario Art. 46 | **5 years** after fiscal year |
| Datos personales | Ley 1581/2012 (Habeas Data) | While necessary for purpose |

**DentalOS conservative policy for Colombia:** 15 years for clinical, 10 years for radiology, 5 years for billing.

### Mexico

| Data Category | Regulation | Retention Period |
|--------------|-----------|-----------------|
| Expediente clínico | NOM-004-SSA3-2012 | **5 years** from last entry |
| Expediente de menores | NOM-004-SSA3-2012 | Until age 18 + 5 years |
| Radiografías | NOM-004-SSA3-2012 | **5 years** |
| CFDI (fiscal) | CFF Art. 30 | **5 years** |

### Chile

| Data Category | Regulation | Retention Period |
|--------------|-----------|-----------------|
| Ficha clínica | Ley 20.584 Art. 12 | **15 years** from last entry |
| Ficha de menores | Ley 20.584 | Until age 18 + 15 years |
| DTE (fiscal) | SII Resolución 61/2019 | **6 years** |

### Consolidated Retention Matrix

| Data Type | Colombia | Mexico | Chile | DentalOS Default |
|-----------|---------|--------|-------|-----------------|
| Clinical records | 20 years | 5 years | 15 years | Uses tenant country |
| Radiographs / X-rays | 10 years | 5 years | 15 years | Uses tenant country |
| Consent forms | 10 years | 5 years | 15 years | Uses tenant country |
| Electronic invoices | 5 years | 5 years | 6 years | Uses tenant country |
| Appointments | 5 years | 5 years | 5 years | 5 years |
| Audit logs | 5 years | 5 years | 5 years | 5 years |
| User activity logs | 2 years | 2 years | 2 years | 2 years |
| System logs | 90 days | 90 days | 90 days | 90 days |

---

## 2. Country Adapter for Retention

Retention periods are resolved via the country adapter pattern (ADR-007 / I-13):

```python
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional


class RetentionPolicy(ABC):
    @abstractmethod
    def clinical_record_retention_years(self) -> int:
        """Minimum retention for clinical records."""
        raise NotImplementedError

    @abstractmethod
    def xray_retention_years(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def consent_retention_years(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def invoice_retention_years(self) -> int:
        raise NotImplementedError

    def can_delete_clinical_record(self, last_modified: date, patient_birth_date: Optional[date]) -> bool:
        """
        Returns True if the record has passed the mandatory retention period.
        Accounts for minor patients (retention extends to adulthood + retention period).
        """
        years_since_modification = (date.today() - last_modified).days / 365.25
        min_years = self.clinical_record_retention_years()

        if patient_birth_date:
            age_at_last_visit = (last_modified - patient_birth_date).days / 365.25
            if age_at_last_visit < 18:
                # Minor: retention starts from 18th birthday
                eighteenth_birthday = date(
                    patient_birth_date.year + 18,
                    patient_birth_date.month,
                    patient_birth_date.day,
                )
                cutoff = date(
                    eighteenth_birthday.year + min_years,
                    eighteenth_birthday.month,
                    eighteenth_birthday.day,
                )
                return date.today() >= cutoff

        cutoff = date(
            last_modified.year + min_years,
            last_modified.month,
            last_modified.day,
        )
        return date.today() >= cutoff


class ColombiaRetentionPolicy(RetentionPolicy):
    def clinical_record_retention_years(self) -> int:
        return 20  # Ley 23/1981

    def xray_retention_years(self) -> int:
        return 10

    def consent_retention_years(self) -> int:
        return 10

    def invoice_retention_years(self) -> int:
        return 5


class MexicoRetentionPolicy(RetentionPolicy):
    def clinical_record_retention_years(self) -> int:
        return 5   # NOM-004

    def xray_retention_years(self) -> int:
        return 5

    def consent_retention_years(self) -> int:
        return 5

    def invoice_retention_years(self) -> int:
        return 5


class ChileRetentionPolicy(RetentionPolicy):
    def clinical_record_retention_years(self) -> int:
        return 15  # Ley 20.584

    def xray_retention_years(self) -> int:
        return 15

    def consent_retention_years(self) -> int:
        return 15

    def invoice_retention_years(self) -> int:
        return 6   # SII requirement


RETENTION_POLICIES = {
    "CO": ColombiaRetentionPolicy(),
    "MX": MexicoRetentionPolicy(),
    "CL": ChileRetentionPolicy(),
}


def get_retention_policy(country_code: str) -> RetentionPolicy:
    return RETENTION_POLICIES.get(country_code, ColombiaRetentionPolicy())
```

---

## 3. Patient Right to Erasure (Derecho al Olvido)

### Principle: Clinical Data Override

Under healthcare regulations in all target countries, the clinical retention mandate **takes priority** over the patient's right to erasure for clinical data. Non-clinical personal data (contact info, preferences) can be anonymized.

### Patient Erasure Request Flow

```python
async def process_erasure_request(
    patient_id: str,
    tenant_id: str,
    requested_by: str,
) -> dict:
    """
    Handle a patient's right-to-erasure request.
    Erases what can be erased; retains what is legally required.
    Returns a report of what was erased vs retained.
    """
    country = await get_tenant_country(tenant_id)
    policy = get_retention_policy(country)

    async with get_tenant_session(tenant_id) as session:
        patient = await get_patient(session, patient_id)
        last_clinical_entry = await get_last_clinical_entry_date(session, patient_id)

        # Determine if clinical data can be erased
        can_erase_clinical = policy.can_delete_clinical_record(
            last_modified=last_clinical_entry,
            patient_birth_date=patient.birth_date,
        )

        erased = []
        retained = []

        if can_erase_clinical:
            # Purge all clinical data
            await purge_patient_clinical_data(session, patient_id)
            erased.extend(["clinical_records", "odontogram", "treatment_plans",
                           "consents", "prescriptions", "xrays", "photos"])
        else:
            # Anonymize identifying data, keep clinical records
            await anonymize_patient_identifiers(session, patient_id)
            erased.extend(["name", "email", "phone", "address", "document_number"])
            retained.extend([
                {
                    "data": "clinical_records",
                    "reason": f"Retención legal obligatoria: {policy.clinical_record_retention_years()} años",
                    "until": (last_clinical_entry.replace(
                        year=last_clinical_entry.year + policy.clinical_record_retention_years()
                    )).isoformat(),
                }
            ])

        # Always erase: marketing preferences, session history
        await purge_patient_non_clinical(session, patient_id)
        erased.extend(["notification_preferences", "portal_sessions", "message_logs"])

        # Log the erasure request and outcome
        await audit_log(
            session, "erasure_request", "patient", patient_id, phi=True,
            metadata={"erased": erased, "retained": [r["data"] for r in retained]}
        )

        return {
            "patient_id": patient_id,
            "erased": erased,
            "retained": retained,
            "processed_at": datetime.utcnow().isoformat(),
        }
```

### Anonymization Strategy

When clinical data must be retained but personal identifiers erased:

```python
async def anonymize_patient_identifiers(session, patient_id: str) -> None:
    """
    Replace PII with anonymized placeholders while preserving clinical data.
    The clinical records remain but are no longer linkable to the individual.
    """
    anon_id = f"ANON-{patient_id[:8].upper()}"

    await session.execute(
        update(Patient)
        .where(Patient.id == patient_id)
        .values(
            first_name="ANONIMIZADO",
            last_name=anon_id,
            email=f"anonimizado-{patient_id[:8]}@invalid.internal",
            phone=None,
            address=None,
            document_number=f"ANON{patient_id[:6]}",
            birth_date=None,                # Remove exact birth date
            birth_year=Patient.birth_year,  # Keep year for age-related clinical context
            photo_key=None,
            is_anonymized=True,
            anonymized_at=datetime.utcnow(),
        )
    )
```

---

## 4. Tenant Lifecycle

### Lifecycle States

```
Active ──(subscription_cancelled)──► Suspended
   │                                     │
   │                                     │ 90 days grace period
   │                                     ▼
   │                               Archived (read-only)
   │                                     │
   │                                     │ after configured archive period
   │                                     ▼
   │                                  Deleted (data purge)
   └─────────────────────────────────────┘
```

| State | Description | Data Access | Duration |
|-------|-------------|------------|---------|
| `active` | Normal operation | Full read/write | While subscribed |
| `suspended` | Payment failed or manually suspended | Read-only + export | Up to 90 days |
| `archived` | Subscription ended, grace period over | Read-only export only | Configured retention period |
| `deleted` | Data purge complete | None | Final |

### Suspension Handler

```python
async def suspend_tenant(tenant_id: str, reason: str) -> None:
    """
    Suspend a tenant account.
    All writes blocked; reads allowed for data export.
    """
    async with get_public_session() as session:
        await session.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(
                status="suspended",
                suspended_at=datetime.utcnow(),
                suspension_reason=reason,
                grace_period_ends_at=datetime.utcnow() + timedelta(days=90),
            )
        )

    # Disable active sessions
    redis = await get_redis()
    await redis.set(f"tenant:status:{tenant_id}", "suspended", ex=90 * 86400)

    # Notify clinic owner
    await enqueue_tenant_suspension_notification(tenant_id, reason)

    # Schedule archival task
    await schedule_archival(tenant_id, run_at=datetime.utcnow() + timedelta(days=90))
```

### Archival Handler

When a suspended tenant's 90-day grace period expires:

```python
async def archive_tenant(tenant_id: str) -> None:
    """
    Archive a tenant:
    1. Generate full data export (JSON + S3 files)
    2. Store export in cold storage
    3. Mark tenant schema as read-only
    4. Send export download link to clinic owner
    """
    # 1. Generate export
    export_path = await generate_tenant_export(tenant_id)

    # 2. Upload to archival bucket
    storage = StorageService()
    archive_key = f"archives/{tenant_id}/export_{date.today().isoformat()}.tar.gz"
    await storage.upload_file(export_path, archive_key, storage_class="GLACIER")

    # 3. Update tenant status
    async with get_public_session() as session:
        await session.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(
                status="archived",
                archived_at=datetime.utcnow(),
                archive_key=archive_key,
            )
        )

    # 4. Notify with download link
    signed_url = storage.generate_presigned_get_url(archive_key, expiry=7 * 86400)
    await enqueue_tenant_archived_notification(tenant_id, signed_url)
```

### Deletion Handler

After the archive period (default: longest retention period for the tenant's country):

```python
async def delete_tenant_data(tenant_id: str) -> None:
    """
    Permanent data purge for a fully archived tenant.
    Requires explicit confirmation by superadmin.
    """
    country = await get_tenant_country(tenant_id)
    policy = get_retention_policy(country)

    # Verify retention period has elapsed
    archived_at = await get_tenant_archived_at(tenant_id)
    min_retention = max(
        policy.clinical_record_retention_years(),
        policy.invoice_retention_years(),
    )
    earliest_deletion = archived_at.replace(year=archived_at.year + min_retention)

    if date.today() < earliest_deletion.date():
        raise RetentionViolation(
            f"No se puede eliminar antes de {earliest_deletion.date().isoformat()}. "
            f"Período de retención legal no cumplido."
        )

    # Drop tenant schema
    async with get_public_session() as engine_conn:
        await engine_conn.execute(
            text(f"DROP SCHEMA IF EXISTS tenant_{tenant_id.replace('-', '')} CASCADE")
        )

    # Delete S3 objects
    await purge_tenant_s3_objects(tenant_id)

    # Remove from public tables
    async with get_public_session() as session:
        await session.execute(
            delete(Tenant).where(Tenant.id == tenant_id)
        )

    # Final audit log in superadmin schema
    await superadmin_audit_log("tenant_deleted", tenant_id)
```

---

## 5. Automated Retention Jobs

### Scheduled Jobs

| Job | Schedule | Action |
|-----|---------|--------|
| `check_suspension_grace_periods` | Daily 2AM | Archive tenants past 90-day grace |
| `check_deletion_eligibility` | Daily 3AM | Alert superadmin of tenants eligible for deletion |
| `purge_expired_import_files` | Daily 4AM | Delete import files older than 30 days |
| `purge_expired_voice_recordings` | Daily 4AM | Delete voice recordings older than 1 year |
| `purge_expired_system_logs` | Daily 5AM | Delete system logs older than 90 days |
| `archive_old_files` | Weekly Sunday 3AM | Move files to archival prefix after 1 year |
| `annual_retention_audit` | January 1st 6AM | Generate retention compliance report |

### Import File Purge

```python
async def purge_expired_import_files() -> None:
    """Delete patient import files older than 30 days (all tenants)."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    storage = StorageService()

    all_tenants = await get_all_active_tenant_ids()
    for tenant_id in all_tenants:
        async with get_tenant_session(tenant_id) as session:
            expired_imports = await get_files_by_type_older_than(
                session, "imports", cutoff
            )
            for file_record in expired_imports:
                await storage.delete_object(file_record.object_key)
                await soft_delete_file_record(session, file_record.id)
```

---

## 6. Annual Retention Compliance Audit

Every year on January 1st, DentalOS generates a retention compliance report:

```python
async def generate_annual_retention_audit() -> dict:
    """
    Generate annual retention compliance report.
    Checks:
    - All tenants have correct retention policies configured
    - No records retained beyond maximum legal period
    - No records deleted before minimum legal period
    - Export data available for archived tenants
    """
    report = {
        "year": date.today().year - 1,
        "generated_at": datetime.utcnow().isoformat(),
        "tenants_reviewed": 0,
        "issues": [],
        "summary": {},
    }

    all_tenants = await get_all_tenants()
    for tenant in all_tenants:
        policy = get_retention_policy(tenant.country)
        issues = await audit_tenant_retention(tenant.id, policy)
        report["tenants_reviewed"] += 1
        if issues:
            report["issues"].extend(issues)

    report["summary"] = {
        "total_issues": len(report["issues"]),
        "compliance_rate": (
            (report["tenants_reviewed"] - len(set(i["tenant_id"] for i in report["issues"])))
            / report["tenants_reviewed"]
        ) if report["tenants_reviewed"] > 0 else 1.0,
    }

    # Store report in superadmin schema
    await store_compliance_report(report)

    # Alert superadmin if issues found
    if report["issues"]:
        await alert_superadmin_compliance_issues(report)

    return report
```

---

## 7. Backup Retention

Database backups have their own retention schedule (separate from data retention — see I-16):

| Backup Type | Retention | Storage |
|-------------|-----------|---------|
| Daily full backup | 30 days | S3 (hot) |
| Weekly full backup | 12 weeks | S3 (hot) |
| Monthly full backup | 12 months | S3 (cold/glacier) |
| WAL segments | 7 days | S3 (hot) |
| Archive backups (deleted tenants) | Per retention policy | S3 (glacier) |

---

## 8. Redis Cache Retention

Redis keys have TTLs set at creation. No manual retention management needed for cache. Relevant TTLs:

| Key Pattern | TTL | Purpose |
|-------------|-----|---------|
| `session:*` | 24h | User JWT sessions |
| `tenant:*` | 1h | Tenant config cache |
| `otp:*` | 10 min | One-time passwords |
| `rate:*` | 1h-24h | Rate limit counters |
| `whatsapp:*` | 24h | WhatsApp session tracking |

---

## 9. Audit Trail for Deletion Events

All data deletion events are logged in the audit table with a special action type:

```python
async def log_deletion_audit(
    tenant_id: str,
    resource_type: str,
    resource_id: str,
    deletion_type: str,  # "erasure_request" | "retention_expiry" | "tenant_purge"
    authorized_by: str,
    country_policy: str,
    retention_period_years: int,
) -> None:
    """Log all data deletion events for compliance audit trail."""
    await audit_log(
        action="delete",
        resource=resource_type,
        resource_id=resource_id,
        tenant_id=tenant_id,
        phi=True,
        metadata={
            "deletion_type": deletion_type,
            "authorized_by": authorized_by,
            "country_policy": country_policy,
            "retention_period_years": retention_period_years,
            "deletion_timestamp": datetime.utcnow().isoformat(),
        }
    )
```

---

## Out of Scope

- GDPR (EU) compliance — DentalOS targets LATAM only for initial launch
- US HIPAA compliance — future if US market entered
- Automated legal holds (litigation hold) — manual process via superadmin
- Per-patient retention override — not supported; country-level only
- Destruction certificates for physical records

---

## Acceptance Criteria

**This policy is complete when:**

- [ ] Country-specific retention periods implemented via adapter pattern
- [ ] Patient erasure request distinguishes erasable vs. legally mandated data
- [ ] Anonymization preserves clinical records while removing personal identifiers
- [ ] Tenant lifecycle transitions (active → suspended → archived → deleted) automated
- [ ] All deletion events logged in audit trail
- [ ] Annual retention audit job generates compliance report
- [ ] Import file purge job removes temporary files after 30 days
- [ ] Voice recording purge job removes audio after 1 year
- [ ] Retention policy verified before allowing data deletion

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
