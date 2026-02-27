#!/usr/bin/env bash
# DentalOS — PostgreSQL full backup script (I-16)
#
# Dumps each tenant schema (tn_*) and the public schema individually.
# Designed for cron execution on the database server.
#
# Usage: ./pg_backup.sh
# Env vars:
#   PGHOST       — PostgreSQL host (default: localhost)
#   PGPORT       — PostgreSQL port (default: 5432)
#   PGUSER       — PostgreSQL user (default: dentalos)
#   PGDATABASE   — Database name (default: dentalos)
#   BACKUP_DIR   — Backup destination (default: /var/backups/dentalos)
#   RETENTION_DAYS — Days to keep backups (default: 30)
#   S3_BUCKET    — Optional S3 bucket for offsite copy
set -euo pipefail

# ─── Configuration ───────────────────────────────────────────────────────────
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-dentalos}"
PGDATABASE="${PGDATABASE:-dentalos}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/dentalos}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_SUBDIR="${BACKUP_DIR}/${TIMESTAMP}"

echo "[$(date -Iseconds)] Starting DentalOS backup..."

# ─── Create backup directory ─────────────────────────────────────────────────
mkdir -p "${BACKUP_SUBDIR}"

# ─── Dump public schema ─────────────────────────────────────────────────────
echo "  Dumping public schema..."
pg_dump \
  -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" \
  --schema=public \
  --format=custom \
  --compress=9 \
  --file="${BACKUP_SUBDIR}/public.dump"

# ─── Dump each tenant schema ────────────────────────────────────────────────
SCHEMAS=$(psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" \
  -t -A -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tn_%' ORDER BY schema_name;")

SCHEMA_COUNT=0
for SCHEMA in ${SCHEMAS}; do
  echo "  Dumping schema: ${SCHEMA}..."
  pg_dump \
    -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" \
    --schema="${SCHEMA}" \
    --format=custom \
    --compress=9 \
    --file="${BACKUP_SUBDIR}/${SCHEMA}.dump"
  SCHEMA_COUNT=$((SCHEMA_COUNT + 1))
done

# ─── Dump globals (roles, tablespaces) ──────────────────────────────────────
echo "  Dumping globals..."
pg_dumpall \
  -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" \
  --globals-only \
  --file="${BACKUP_SUBDIR}/globals.sql"

# ─── Create manifest ────────────────────────────────────────────────────────
cat > "${BACKUP_SUBDIR}/manifest.json" <<EOF
{
  "timestamp": "${TIMESTAMP}",
  "database": "${PGDATABASE}",
  "host": "${PGHOST}",
  "schemas_backed_up": ${SCHEMA_COUNT},
  "includes_public": true,
  "includes_globals": true,
  "format": "custom",
  "compression": 9
}
EOF

# ─── Optional S3 upload ─────────────────────────────────────────────────────
if [ -n "${S3_BUCKET:-}" ]; then
  echo "  Uploading to S3: ${S3_BUCKET}..."
  aws s3 sync "${BACKUP_SUBDIR}" "s3://${S3_BUCKET}/pg-backups/${TIMESTAMP}/" --quiet
fi

# ─── Cleanup old backups ────────────────────────────────────────────────────
echo "  Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -exec rm -rf {} +

# ─── Summary ─────────────────────────────────────────────────────────────────
TOTAL_SIZE=$(du -sh "${BACKUP_SUBDIR}" | cut -f1)
echo "[$(date -Iseconds)] Backup complete: ${SCHEMA_COUNT} tenant schemas + public + globals (${TOTAL_SIZE})"
echo "  Location: ${BACKUP_SUBDIR}"
