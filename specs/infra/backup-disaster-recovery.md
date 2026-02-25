# Backup and Disaster Recovery Spec

> **Spec ID:** I-16
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Backup strategy and disaster recovery procedures for DentalOS. PostgreSQL uses continuous WAL archiving to S3 with Point-in-Time Recovery (PITR). Full backups run daily. Cross-region backup copies ensure geographic redundancy. S3 versioning protects object storage. RTO target: 4 hours. RPO target: 1 hour. Monthly DR drills required. All backups encrypted with AES-256.

**Domain:** infra

**Priority:** Critical

**Dependencies:** I-14 (deployment-architecture), I-15 (monitoring-observability), I-12 (data-retention)

---

## 1. Recovery Objectives

| Metric | Target | Description |
|--------|--------|-------------|
| **RTO** (Recovery Time Objective) | **4 hours** | Maximum time to restore service after total failure |
| **RPO** (Recovery Point Objective) | **1 hour** | Maximum data loss window (at most 1 hour of transactions) |
| WAL archival frequency | Continuous (~1 min lag) | Near-real-time WAL shipping to S3 |
| Full backup frequency | Daily at 3AM UTC-5 | `pg_basebackup` or Hetzner snapshot |
| Backup verification | Weekly | Automated restore test to isolated environment |

---

## 2. PostgreSQL Backup Strategy

### Architecture

```
PostgreSQL (Hetzner Managed CPX31)
    │
    ├── Continuous WAL Archiving → S3 (dentalos-backups/wal/)
    │   └── pg_wal_archive_command → every WAL segment (~16MB / 1-2 min)
    │
    ├── Daily Full Backup (3AM UTC-5)
    │   └── pg_basebackup → S3 (dentalos-backups/full/{date}/)
    │
    └── Hetzner Volume Snapshot (weekly)
        └── Stored in Hetzner Snapshot storage
```

### WAL Archiving Configuration

```ini
# postgresql.conf additions for WAL archiving
wal_level = replica
archive_mode = on
archive_command = '/opt/dentalos/scripts/wal_archive.sh %f %p'
archive_timeout = 60            # Force WAL switch every 60 seconds maximum
max_wal_size = 1GB
min_wal_size = 80MB
wal_keep_size = 1GB             # Keep 1GB of WAL on local disk
```

**WAL archive script:**

```bash
#!/bin/bash
# /opt/dentalos/scripts/wal_archive.sh
# Encrypts and uploads WAL segments to S3

WAL_FILENAME="$1"
WAL_PATH="$2"
S3_BUCKET="dentalos-backups"
S3_PREFIX="wal/$(date +%Y/%m/%d)"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY}"

# Encrypt WAL segment
openssl enc -aes-256-gcm \
    -K "${ENCRYPTION_KEY}" \
    -iv "$(openssl rand -hex 12)" \
    -in "${WAL_PATH}" \
    -out "${WAL_PATH}.enc" 2>/dev/null

# Upload to S3
aws s3 cp "${WAL_PATH}.enc" \
    "s3://${S3_BUCKET}/${S3_PREFIX}/${WAL_FILENAME}.enc" \
    --endpoint-url "${S3_ENDPOINT_URL}" \
    --storage-class STANDARD \
    --sse AES256

STATUS=$?
rm -f "${WAL_PATH}.enc"

if [ $STATUS -ne 0 ]; then
    echo "ERROR: WAL archive failed for ${WAL_FILENAME}" >&2
    exit 1
fi

exit 0
```

### Daily Full Backup

```bash
#!/bin/bash
# /opt/dentalos/scripts/full_backup.sh
# Runs at 03:00 UTC-5 (08:00 UTC) daily via cron

set -euo pipefail

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/tmp/dentalos-backup-${DATE}"
S3_BUCKET="dentalos-backups"
S3_PREFIX="full/${DATE}"
POSTGRES_HOST="${POSTGRES_HOST}"
POSTGRES_USER="${POSTGRES_USER}"
LOG_FILE="/var/log/dentalos/backup-${DATE}.log"

echo "[$(date)] Starting full backup for ${DATE}" | tee -a "$LOG_FILE"

# 1. Create backup using pg_basebackup
mkdir -p "$BACKUP_DIR"
PGPASSWORD="${POSTGRES_PASSWORD}" pg_basebackup \
    -h "$POSTGRES_HOST" \
    -U "$POSTGRES_USER" \
    -D "$BACKUP_DIR" \
    -Ft \                        # Tar format
    -z \                         # Gzip compression
    -P \                         # Progress reporting
    --wal-method=stream \        # Include WAL files
    2>&1 | tee -a "$LOG_FILE"

# 2. Encrypt the backup
for file in "$BACKUP_DIR"/*.tar.gz; do
    openssl enc -aes-256-gcm \
        -K "${BACKUP_ENCRYPTION_KEY}" \
        -iv "$(openssl rand -hex 12)" \
        -in "$file" \
        -out "${file}.enc"
    rm "$file"
done

# 3. Calculate SHA-256 checksums
for file in "$BACKUP_DIR"/*.enc; do
    sha256sum "$file" >> "$BACKUP_DIR/checksums.sha256"
done

# 4. Upload to primary S3 (Hetzner FSN1)
aws s3 sync "$BACKUP_DIR" \
    "s3://${S3_BUCKET}/${S3_PREFIX}/" \
    --endpoint-url "${S3_ENDPOINT_URL_FSN1}" \
    --sse AES256 \
    2>&1 | tee -a "$LOG_FILE"

# 5. Cross-region copy to secondary DC (Hetzner NBG1)
aws s3 sync "$BACKUP_DIR" \
    "s3://${S3_BUCKET_SECONDARY}/${S3_PREFIX}/" \
    --endpoint-url "${S3_ENDPOINT_URL_NBG1}" \
    --sse AES256 \
    2>&1 | tee -a "$LOG_FILE"

# 6. Cleanup local files
rm -rf "$BACKUP_DIR"

# 7. Verify backup was uploaded
UPLOADED_SIZE=$(aws s3 ls --recursive \
    "s3://${S3_BUCKET}/${S3_PREFIX}/" \
    --endpoint-url "${S3_ENDPOINT_URL_FSN1}" | \
    awk '{sum += $3} END {print sum}')

if [ "$UPLOADED_SIZE" -lt 1000000 ]; then
    echo "[$(date)] ERROR: Backup appears incomplete (${UPLOADED_SIZE} bytes)" | tee -a "$LOG_FILE"
    # Alert via Telegram
    /opt/dentalos/scripts/alert.sh "P1" "Backup failed" "Full backup ${DATE} appears incomplete"
    exit 1
fi

echo "[$(date)] Full backup completed successfully. Size: ${UPLOADED_SIZE} bytes" | tee -a "$LOG_FILE"

# 8. Log backup metadata to DentalOS database
psql "$DATABASE_URL" -c "
    INSERT INTO superadmin.backup_log (backup_type, backup_date, s3_prefix, size_bytes, status)
    VALUES ('full', '${DATE}', '${S3_PREFIX}', ${UPLOADED_SIZE}, 'success');
"
```

---

## 3. Backup Retention Schedule

| Backup Type | Retention | Storage Class | Notes |
|------------|-----------|--------------|-------|
| Daily full backup | 30 days | Standard S3 | Last month of daily backups |
| Weekly full backup | 12 weeks | Standard S3 | Retained from daily set |
| Monthly full backup | 12 months | Cold/Glacier | First backup of each month |
| WAL segments | 7 days | Standard S3 | Rolling window for PITR |
| Hetzner Volume Snapshot | 4 weeks | Hetzner Snapshots | Emergency OS-level recovery |
| Archive backup (deleted tenants) | Per retention policy | Glacier | See I-12 |

### Automated Retention Cleanup

```bash
# Cron: 1st of each month at 4AM UTC-5
/opt/dentalos/scripts/cleanup_old_backups.sh

# cleanup_old_backups.sh:
# - Delete daily backups older than 30 days
# - Delete WAL segments older than 7 days
# - Move monthly backup (1st of month) to cold storage tier
```

---

## 4. S3 Object Storage Backup

### Versioning

All production S3 buckets have versioning enabled:

```bash
aws s3api put-bucket-versioning \
    --bucket dentalos-prod \
    --versioning-configuration Status=Enabled \
    --endpoint-url "${S3_ENDPOINT_URL}"
```

With versioning:
- Accidentally deleted files can be restored within 30 days
- Overwritten files retain previous versions
- Versioned objects are not counted toward retention; apply lifecycle rules to expire old versions

### Lifecycle Rules

```json
{
  "Rules": [
    {
      "Id": "expire-old-versions",
      "Status": "Enabled",
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 30
      }
    },
    {
      "Id": "transition-archive-to-cold",
      "Status": "Enabled",
      "Prefix": "*/archive/",
      "Transitions": [
        {
          "Days": 365,
          "StorageClass": "GLACIER"
        }
      ]
    },
    {
      "Id": "expire-import-files",
      "Status": "Enabled",
      "Prefix": "*/imports/",
      "Expiration": {
        "Days": 30
      }
    }
  ]
}
```

### Cross-Region Replication

S3 replication configured from Hetzner FSN1 (primary) to Hetzner NBG1 (Nuremberg, secondary):

```bash
aws s3api put-bucket-replication \
    --bucket dentalos-prod \
    --replication-configuration '{
        "Role": "arn:aws:iam::...",
        "Rules": [{
            "Status": "Enabled",
            "Destination": {
                "Bucket": "arn:aws:s3:::dentalos-prod-nbg1"
            }
        }]
    }' \
    --endpoint-url "${S3_ENDPOINT_URL_FSN1}"
```

---

## 5. Backup Encryption

All backups are encrypted with AES-256 at two levels:

### Level 1: S3 Server-Side Encryption (SSE)

Hetzner Object Storage SSE-S3 encrypts data at rest using S3-managed keys. Applied via `--sse AES256` flag on all uploads.

### Level 2: Application-Level Encryption

Database backups are additionally encrypted with a DentalOS-managed key before upload:

```python
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64


def encrypt_backup(plaintext_path: str, output_path: str, key_hex: str) -> str:
    """
    Encrypt a backup file with AES-256-GCM.
    Returns the IV (nonce) as hex, stored alongside the ciphertext in the filename.
    """
    key = bytes.fromhex(key_hex)
    nonce = os.urandom(12)  # 96-bit nonce

    with open(plaintext_path, "rb") as f:
        plaintext = f.read()

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)

    # Write nonce + ciphertext
    with open(output_path, "wb") as f:
        f.write(nonce + ciphertext)

    return nonce.hex()


def decrypt_backup(encrypted_path: str, output_path: str, key_hex: str) -> None:
    """Decrypt a backup file during recovery."""
    key = bytes.fromhex(key_hex)

    with open(encrypted_path, "rb") as f:
        data = f.read()

    nonce = data[:12]
    ciphertext = data[12:]

    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)

    with open(output_path, "wb") as f:
        f.write(plaintext)
```

**Encryption key management:**
- Backup encryption key stored in environment variable `BACKUP_ENCRYPTION_KEY`
- Key is separate from the PHI master key
- Key stored in secure offline location (printed + sealed envelope in physical safe)
- Rotation: annually, with re-encryption of all existing backups

---

## 6. Disaster Recovery Runbook

### Scenarios and Response Procedures

#### Scenario 1: Single App Server Failure

**Impact:** Reduced capacity; load balancer routes to remaining server
**RTO:** 15 minutes (Hetzner provisions new server in ~5 min)

```
Steps:
1. Hetzner LB detects unhealthy server → routes to App Server 2
2. Alert fires (P2 — app server down)
3. Create new CX41 server in Hetzner
4. Run bootstrap script: install dependencies, deploy latest Docker image
5. Add to load balancer
6. Verify health check passes on new server
7. Investigate old server failure (if still accessible)
```

#### Scenario 2: Database Server Failure (Hetzner Managed PG)

**Impact:** All write operations fail; read replicas may work briefly
**RTO:** 4 hours
**RPO:** ~1 hour (last WAL archive)

```
Steps:
1. Alert fires (P1 — database connection lost)
2. Assess: is Hetzner Managed PG responding?
   a. YES — check connection limits, restart PgBouncer
   b. NO — initiate recovery
3. Create new PostgreSQL instance (Hetzner Managed or self-hosted CPX31)
4. Restore from latest full backup:
   a. Download latest full backup from S3
   b. Decrypt backup
   c. Restore base backup: pg_restore or extract tar
   d. Configure WAL recovery (recovery.conf)
5. Apply WAL archives up to desired recovery point:
   restore_command = '/opt/dentalos/scripts/wal_restore.sh %f %p'
6. Start PostgreSQL in recovery mode
7. Verify data consistency (check latest transaction timestamp)
8. Update DATABASE_URL in app server .env files
9. Restart app servers
10. Verify health check returns healthy
Total estimated time: 2-4 hours
```

**WAL restore script:**

```bash
#!/bin/bash
# /opt/dentalos/scripts/wal_restore.sh
WAL_FILENAME="$1"
RESTORE_PATH="$2"
S3_BUCKET="dentalos-backups"

# Try primary DC first, then secondary
for ENDPOINT in "${S3_ENDPOINT_URL_FSN1}" "${S3_ENDPOINT_URL_NBG1}"; do
    aws s3 cp \
        "s3://${S3_BUCKET}/wal/$(date +%Y/%m/%d)/${WAL_FILENAME}.enc" \
        "/tmp/${WAL_FILENAME}.enc" \
        --endpoint-url "$ENDPOINT" 2>/dev/null

    if [ $? -eq 0 ]; then
        # Decrypt
        openssl enc -d -aes-256-gcm \
            -K "${BACKUP_ENCRYPTION_KEY}" \
            -in "/tmp/${WAL_FILENAME}.enc" \
            -out "$RESTORE_PATH"
        rm -f "/tmp/${WAL_FILENAME}.enc"
        exit 0
    fi
done

exit 1  # WAL segment not found
```

#### Scenario 3: Total Datacenter Failure (Hetzner FSN1 down)

**Impact:** All services unavailable
**RTO:** 4 hours (cross-region failover)
**RPO:** ~1 hour

```
Steps:
1. Confirm FSN1 datacenter is unreachable
2. Provision replacement infrastructure in Hetzner NBG1 (Nuremberg):
   a. Create app servers, worker server, DB server in NBG1
   b. Update firewall rules
3. Restore PostgreSQL from secondary S3 bucket (NBG1):
   a. Latest full backup + WAL archives
4. Update DNS:
   a. Point api.dentalos.app, app.dentalos.app to new NBG1 IPs
   b. TTL should be set to 300s (5 min) to enable fast DNS failover
5. Deploy application to new servers
6. Run smoke tests
7. Update status page
Estimated time: 3-5 hours
```

#### Scenario 4: S3 Object Storage Loss

**Impact:** Files (X-rays, photos, PDFs) inaccessible; clinical and billing records in DB intact
**RTO:** 2 hours (switch to secondary region bucket)

```
Steps:
1. Update S3_ENDPOINT_URL env var to point to secondary Hetzner DC bucket
2. Restart app servers
3. Verify file access via signed URLs
4. Files in secondary bucket are a replica (may be slightly behind)
5. Log incident for audit
```

#### Scenario 5: Ransomware / Data Corruption

**Impact:** Data corrupted or encrypted
**RTO:** 4-8 hours
**RPO:** Last clean backup

```
Steps:
1. Isolate compromised servers (disable LB, shut down app servers)
2. Preserve evidence (take snapshot before any cleanup)
3. Provision fresh infrastructure (new servers, clean installs)
4. Restore from last known-good backup (before corruption event)
5. Audit changes since last clean backup
6. Notify affected tenants if patient data was accessed
7. Post-incident security review
```

---

## 7. Backup Verification (Weekly)

Every Sunday at 4AM UTC-5, an automated verification job:

```bash
#!/bin/bash
# /opt/dentalos/scripts/verify_backup.sh
# Restores latest backup to an isolated test database and runs verification queries

set -euo pipefail

DATE=$(date +%Y-%m-%d)
TEST_DB="dentalos_backup_verify_$(date +%s)"

echo "[$(date)] Starting backup verification for ${DATE}"

# 1. Download latest full backup
aws s3 cp \
    "s3://dentalos-backups/full/${DATE}/base.tar.gz.enc" \
    "/tmp/base.tar.gz.enc" \
    --endpoint-url "${S3_ENDPOINT_URL}"

# 2. Decrypt and extract
decrypt_backup "/tmp/base.tar.gz.enc" "/tmp/base.tar.gz"
mkdir -p "/tmp/restore_test"
tar xzf "/tmp/base.tar.gz" -C "/tmp/restore_test"

# 3. Start temporary PostgreSQL instance
pg_ctl -D "/tmp/restore_test" start
sleep 3

# 4. Run verification queries
RESTORE_URL="postgresql://localhost/postgres"
TENANT_COUNT=$(psql "$RESTORE_URL" -tAc "SELECT COUNT(*) FROM public.tenants WHERE status='active'")
PATIENT_COUNT=$(psql "$RESTORE_URL" -tAc "SELECT SUM(count) FROM (SELECT COUNT(*) as count FROM information_schema.tables WHERE table_name='patients') t")

echo "Verification: ${TENANT_COUNT} active tenants found"

if [ "$TENANT_COUNT" -gt 0 ]; then
    echo "SUCCESS: Backup verification passed"
    VERIFY_STATUS="success"
else
    echo "WARNING: No active tenants found in backup"
    VERIFY_STATUS="warning"
fi

# 5. Cleanup
pg_ctl -D "/tmp/restore_test" stop
rm -rf "/tmp/restore_test" "/tmp/base.tar.gz" "/tmp/base.tar.gz.enc"

# 6. Log result
psql "$DATABASE_URL" -c "
    UPDATE superadmin.backup_log
    SET verify_status = '${VERIFY_STATUS}', verified_at = NOW()
    WHERE backup_date = '${DATE}' AND backup_type = 'full';
"

echo "[$(date)] Backup verification complete: ${VERIFY_STATUS}"
```

---

## 8. Monthly DR Drill

Every month, the engineering team executes a simulated disaster recovery:

**DR Drill Checklist:**

- [ ] Pull latest full backup + WAL from S3
- [ ] Restore to isolated test environment
- [ ] Verify data integrity (tenant count, patient count, latest appointment)
- [ ] Measure actual RTO (time from "incident declared" to "service restored")
- [ ] Measure actual RPO (time difference between last record and backup)
- [ ] Test DNS failover procedure (update to staging IPs)
- [ ] Document any gaps between target and actual RTO/RPO
- [ ] Update runbook if procedures need adjustment

**Results logged in:** `superadmin.dr_drill_log`

---

## 9. Backup Monitoring and Alerting

```python
# Backup monitoring job — runs after each backup
async def verify_recent_backup_exists() -> None:
    """
    Check that a full backup was created in the last 25 hours.
    Alert if backup is overdue.
    """
    last_backup = await get_latest_backup_record()
    if not last_backup:
        await send_alert("P1", "No backup records found", "")
        return

    hours_since_backup = (datetime.utcnow() - last_backup.created_at).total_seconds() / 3600
    if hours_since_backup > 25:
        await send_alert(
            "P1",
            f"Backup overdue: last backup {hours_since_backup:.1f}h ago",
            "Expected: daily at 3AM UTC-5",
        )
    elif last_backup.status != "success":
        await send_alert(
            "P2",
            f"Last backup failed: {last_backup.status}",
            f"Date: {last_backup.backup_date}",
        )
```

**Alert rules:**

| Alert | Condition | Severity |
|-------|-----------|---------|
| Backup overdue | No full backup in 25h | P1 |
| Backup failed | `backup_log.status != 'success'` | P1 |
| WAL archiving lagging | WAL lag > 2h | P2 |
| Backup storage full | Bucket > 80% capacity | P2 |
| Verify failed | Weekly verify returned warning/error | P2 |
| Encryption key missing | `BACKUP_ENCRYPTION_KEY` not set | P1 |

---

## 10. Backup Table (Superadmin Schema)

```sql
CREATE TABLE superadmin.backup_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_type     VARCHAR(20) NOT NULL,      -- full | wal | snapshot | archive
    backup_date     DATE NOT NULL,
    s3_prefix       VARCHAR(500),
    size_bytes      BIGINT,
    status          VARCHAR(20) DEFAULT 'pending',  -- pending | success | failed
    verify_status   VARCHAR(20),                    -- success | warning | failed | NULL
    verified_at     TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE superadmin.dr_drill_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drill_date      DATE NOT NULL,
    actual_rto_minutes INTEGER,
    actual_rpo_minutes INTEGER,
    target_rto_minutes INTEGER DEFAULT 240,
    target_rpo_minutes INTEGER DEFAULT 60,
    passed          BOOLEAN,
    notes           TEXT,
    conducted_by    VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## Out of Scope

- Hot standby / streaming replication — not needed for initial scale (PITR from S3 is sufficient)
- Multi-master PostgreSQL — overkill for v1
- Automated failover (DNS auto-switch) — manual failover is acceptable given 4h RTO
- Backup of Redis state — Redis is cache-only; loss is acceptable (cache rebuilds automatically)
- Backup of RabbitMQ queues — in-flight messages may be lost on failure; this is acceptable for notification queues

---

## Acceptance Criteria

**This spec is complete when:**

- [ ] WAL archiving configured and uploading to S3 every < 2 minutes
- [ ] Daily full backup runs and uploads to both primary and secondary DC
- [ ] Backup files are encrypted (AES-256-GCM) before S3 upload
- [ ] S3 versioning enabled on production bucket
- [ ] Weekly automated restore verification runs and passes
- [ ] Backup monitoring alert fires within 2 hours of backup failure
- [ ] DR runbook reviewed by at least 2 engineers
- [ ] First monthly DR drill completed and RTO ≤ 4 hours achieved
- [ ] Encryption key stored securely offline (not only in environment variable)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
