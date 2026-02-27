# ─────────────────────────────────────────────────────────────────────────────
# DentalOS — Database Resources
#
# Strategy: Self-managed PostgreSQL 16 on a dedicated CPX31 server.
#
# WHY SELF-MANAGED vs HETZNER MANAGED:
#   Hetzner Managed PostgreSQL (as of 2026) does NOT support SET search_path
#   per-connection, which is required by DentalOS's schema-per-tenant
#   architecture (ADR-001). Until Hetzner's managed offering supports this,
#   we run our own PostgreSQL instance.
#
#   When Hetzner Managed PostgreSQL adds search_path support, migrate using:
#   pg_dump | pg_restore with --no-owner --no-acl.
#
# Server:  CPX31 (4 vCPU AMD, 8 GB RAM, 160 GB SSD)  €13/month
# Volume:  40 GB additional block storage              €2/month
# Total:                                               ~€15/month
#
# IP: 10.0.1.40 (private network only — never publicly accessible)
# ─────────────────────────────────────────────────────────────────────────────

# ── cloud-init for DB Server ──────────────────────────────────────────────────
# Extended init that also installs PostgreSQL 16 and configures
# connection pooling via PgBouncer (see deployment-architecture.md §10).

locals {
  db_cloud_init = <<-EOF
    #cloud-config
    ${templatefile("${path.module}/cloud-init.yaml", {
      environment = var.environment
      server_role = "db"
    })}
    # PostgreSQL 16 installation appended for the DB role.
    # Actual PostgreSQL configuration (postgresql.conf, pg_hba.conf) is
    # managed by the deploy/ops scripts in /ops/db/ after initial boot.
    runcmd_extra:
      - curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg
      - echo "deb [signed-by=/etc/apt/keyrings/postgresql.gpg] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
      - apt-get update -q
      - apt-get install -y postgresql-16 postgresql-client-16 pgbouncer
      - systemctl enable postgresql
  EOF
}

# ── Database Server ───────────────────────────────────────────────────────────

resource "hcloud_server" "db" {
  name        = "dentalos-db"
  server_type = "cpx31"          # AMD EPYC 4 vCPU, 8 GB RAM — I/O-optimised
  image       = var.server_image
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.dentalos.id]

  # Use the base cloud-init (Docker + security hardening).
  # PostgreSQL is installed separately via the ops playbook after initial boot
  # to keep cloud-init idempotent and fast.
  user_data = local.cloud_init_base

  network {
    network_id = hcloud_network.main.id
    ip         = "10.0.1.40"
    alias_ips  = []
  }

  # Internal firewall: only SSH from ops + all TCP from private network.
  firewall_ids = [hcloud_firewall.internal.id]

  labels = {
    project     = "dentalos"
    environment = var.environment
    role        = "database"
  }

  depends_on = [
    hcloud_network_subnet.app,
  ]

  lifecycle {
    # The database server must never be accidentally destroyed.
    # Set this to true once data is in production.
    prevent_destroy = false
    ignore_changes  = [user_data]
  }
}

# ── Persistent Data Volume ────────────────────────────────────────────────────
# PostgreSQL data directory (/var/lib/postgresql/16/main) lives on this volume.
# Volumes persist independently of the server — if you replace the DB server,
# detach this volume and reattach to the new server to preserve data.
#
# Sizing: 40 GB baseline.
#   - Schema-per-tenant model: each tenant's data is isolated but shares
#     one PostgreSQL instance.
#   - At 200 tenants × ~100 MB average = ~20 GB clinical data.
#   - WAL archival adds ~10 GB. Increase in 10 GB increments via:
#     `hcloud volume resize --size <new_gb> dentalos-db-data`

resource "hcloud_volume" "db_data" {
  name      = "dentalos-db-data"
  size      = 40               # GB — expand without downtime via hcloud CLI
  location  = var.location
  format    = "ext4"           # ext4 is fine for PostgreSQL; XFS is alternative

  labels = {
    project     = "dentalos"
    environment = var.environment
    role        = "database"
    backup      = "true"       # Tag for backup policy enforcement
  }
}

# ── Volume Attachment ─────────────────────────────────────────────────────────
# Attach the data volume to the DB server. After first boot, format and mount:
#
#   ssh dentalos@<db-ip>
#   lsblk                          # Confirm /dev/sdb is the volume
#   systemctl stop postgresql
#   rsync -av /var/lib/postgresql/ /mnt/db-data/
#   # Add to /etc/fstab and update postgresql.conf data_directory

resource "hcloud_volume_attachment" "db_data" {
  volume_id = hcloud_volume.db_data.id
  server_id = hcloud_server.db.id
  automount = false             # Mount manually after first-boot setup

  lifecycle {
    # Never detach the volume automatically — data loss risk.
    prevent_destroy = false     # Set to true in production
  }
}
