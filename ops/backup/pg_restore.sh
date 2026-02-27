#!/usr/bin/env bash
# DentalOS — PostgreSQL restore script
#
# Restores from a backup created by pg_backup.sh.
#
# Usage:
#   ./pg_restore.sh <backup_dir>                    # Restore all schemas
#   ./pg_restore.sh <backup_dir> --schema tn_abc123 # Restore single tenant
#   ./pg_restore.sh <backup_dir> --schema public    # Restore public schema only
#
# WARNING: This will DROP and RECREATE the target schema(s).
# Always test on a staging environment first.
set -euo pipefail

# ─── Parse arguments ─────────────────────────────────────────────────────────
BACKUP_DIR="${1:?Usage: pg_restore.sh <backup_dir> [--schema <schema_name>]}"
TARGET_SCHEMA=""

if [ "${2:-}" = "--schema" ]; then
  TARGET_SCHEMA="${3:?--schema requires a schema name}"
fi

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-dentalos}"
PGDATABASE="${PGDATABASE:-dentalos}"

# ─── Validate backup directory ───────────────────────────────────────────────
if [ ! -f "${BACKUP_DIR}/manifest.json" ]; then
  echo "ERROR: No manifest.json found in ${BACKUP_DIR}. Is this a valid backup?"
  exit 1
fi

echo "[$(date -Iseconds)] Starting DentalOS restore from: ${BACKUP_DIR}"
echo "  Target database: ${PGDATABASE}@${PGHOST}:${PGPORT}"

# ─── Restore function ───────────────────────────────────────────────────────
restore_schema() {
  local schema_name="$1"
  local dump_file="${BACKUP_DIR}/${schema_name}.dump"

  if [ ! -f "${dump_file}" ]; then
    echo "  WARNING: Dump file not found for schema '${schema_name}', skipping."
    return 0
  fi

  echo "  Restoring schema: ${schema_name}..."

  # Drop and recreate the schema
  psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" \
    -c "DROP SCHEMA IF EXISTS \"${schema_name}\" CASCADE;" \
    -c "CREATE SCHEMA \"${schema_name}\";"

  # Restore from custom format dump
  pg_restore \
    -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" \
    --schema="${schema_name}" \
    --no-owner \
    --no-privileges \
    --single-transaction \
    "${dump_file}"

  echo "  Schema '${schema_name}' restored successfully."
}

# ─── Execute restore ─────────────────────────────────────────────────────────
if [ -n "${TARGET_SCHEMA}" ]; then
  # Restore single schema
  restore_schema "${TARGET_SCHEMA}"
else
  # Restore globals first
  if [ -f "${BACKUP_DIR}/globals.sql" ]; then
    echo "  Restoring globals..."
    psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" \
      -f "${BACKUP_DIR}/globals.sql" 2>/dev/null || true
  fi

  # Restore public schema
  restore_schema "public"

  # Restore all tenant schemas
  for dump_file in "${BACKUP_DIR}"/tn_*.dump; do
    [ -f "${dump_file}" ] || continue
    schema_name=$(basename "${dump_file}" .dump)
    restore_schema "${schema_name}"
  done
fi

echo "[$(date -Iseconds)] Restore complete."
