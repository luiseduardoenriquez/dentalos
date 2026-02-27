#!/usr/bin/env bash
# DentalOS — WAL archive command for continuous archiving / PITR
#
# Used as archive_command in postgresql.conf:
#   archive_command = '/opt/dentalos/ops/backup/pg_wal_archive.sh %p %f'
#
# %p = path to WAL file to archive
# %f = filename of WAL file
set -euo pipefail

WAL_SOURCE="$1"
WAL_FILENAME="$2"
ARCHIVE_DIR="${WAL_ARCHIVE_DIR:-/var/backups/dentalos/wal}"
S3_BUCKET="${S3_BUCKET:-}"

mkdir -p "${ARCHIVE_DIR}"

# Copy to local archive
cp "${WAL_SOURCE}" "${ARCHIVE_DIR}/${WAL_FILENAME}"

# Optional: upload to S3 for offsite DR
if [ -n "${S3_BUCKET}" ]; then
  aws s3 cp "${ARCHIVE_DIR}/${WAL_FILENAME}" \
    "s3://${S3_BUCKET}/wal-archive/${WAL_FILENAME}" --quiet
fi

# Cleanup WAL files older than 7 days (keep recent for PITR)
find "${ARCHIVE_DIR}" -maxdepth 1 -type f -mtime +7 -delete

echo "[$(date -Iseconds)] WAL archived: ${WAL_FILENAME}"
