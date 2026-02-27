# DentalOS — Backup & Disaster Recovery

## Overview

DentalOS uses a multi-layer backup strategy for PostgreSQL:

1. **Full schema dumps** (`pg_backup.sh`) — nightly, per-schema custom format
2. **WAL archiving** (`pg_wal_archive.sh`) — continuous, enables Point-in-Time Recovery (PITR)
3. **Optional S3 offsite** — automatic upload when `S3_BUCKET` is set

## Quick Start

### Nightly Full Backup (cron)

```bash
# Add to crontab (runs at 2:00 AM daily)
0 2 * * * /opt/dentalos/ops/backup/pg_backup.sh >> /var/log/dentalos-backup.log 2>&1
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PGHOST` | `localhost` | PostgreSQL host |
| `PGPORT` | `5432` | PostgreSQL port |
| `PGUSER` | `dentalos` | PostgreSQL user |
| `PGDATABASE` | `dentalos` | Database name |
| `BACKUP_DIR` | `/var/backups/dentalos` | Local backup directory |
| `RETENTION_DAYS` | `30` | Days to keep local backups |
| `S3_BUCKET` | *(empty)* | S3 bucket for offsite copies |
| `WAL_ARCHIVE_DIR` | `/var/backups/dentalos/wal` | WAL archive directory |

### Enable WAL Archiving

1. Copy `postgresql.conf.snippet` settings to your `postgresql.conf`
2. Adjust `archive_command` path as needed
3. Restart PostgreSQL: `sudo systemctl restart postgresql`

### Restore

```bash
# Restore all schemas from a specific backup
./pg_restore.sh /var/backups/dentalos/20260226_020000

# Restore a single tenant schema
./pg_restore.sh /var/backups/dentalos/20260226_020000 --schema tn_abc123

# Restore only the public schema
./pg_restore.sh /var/backups/dentalos/20260226_020000 --schema public
```

### Point-in-Time Recovery (PITR)

For recovering to a specific point in time:

```bash
# 1. Stop PostgreSQL
sudo systemctl stop postgresql

# 2. Restore base backup
./pg_restore.sh /var/backups/dentalos/20260226_020000

# 3. Configure recovery in postgresql.conf:
#    restore_command = 'cp /var/backups/dentalos/wal/%f %p'
#    recovery_target_time = '2026-02-26 15:30:00 UTC'

# 4. Create recovery signal
touch $PGDATA/recovery.signal

# 5. Start PostgreSQL (it will replay WAL up to target time)
sudo systemctl start postgresql
```

## Security Notes

- Backup files contain **all clinical data** — treat as PHI
- Encrypt backups at rest (S3 SSE or GPG)
- Restrict backup directory permissions: `chmod 700 /var/backups/dentalos`
- Use `.pgpass` file for automated password — never pass via CLI
- Audit backup access logs
