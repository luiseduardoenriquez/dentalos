# ─────────────────────────────────────────────────────────────────────────────
# DentalOS — Server Resources
#
# Topology:
#   app1    10.0.1.10  CX41 (8 vCPU, 16GB)  FastAPI + Next.js  €17/mo
#   app2    10.0.1.11  CX41 (8 vCPU, 16GB)  FastAPI + Next.js  €17/mo
#   worker  10.0.1.20  CPX31 (4 vCPU, 8GB)  RabbitMQ + workers €13/mo
#   redis   10.0.1.30  CX21 (2 vCPU, 4GB)   Redis 7            €6/mo
#
# DB server is in database.tf (CPX31 self-managed, 10.0.1.40).
# ─────────────────────────────────────────────────────────────────────────────

# ── SSH Key ───────────────────────────────────────────────────────────────────
# The public key is uploaded once to Hetzner and injected into every server
# via cloud-init. Store the corresponding private key in your password manager.

resource "hcloud_ssh_key" "dentalos" {
  name       = "dentalos-${var.environment}"
  public_key = file(var.ssh_public_key_path)

  labels = {
    project     = "dentalos"
    environment = var.environment
  }
}

# ── cloud-init user_data ──────────────────────────────────────────────────────
# A single base template is used for all servers. The server_role variable
# is passed through so the script can install role-specific packages if needed.

locals {
  cloud_init_base = templatefile("${path.module}/cloud-init.yaml", {
    environment = var.environment
    server_role = "base"
  })
}

# ── App Server 1 ──────────────────────────────────────────────────────────────
# Primary application server. Also runs Alembic migrations during deploys.
# The load balancer forwards ~50% of traffic here.

resource "hcloud_server" "app1" {
  name        = "dentalos-app1"
  server_type = "cx41"          # 8 vCPU, 16 GB RAM, 160 GB SSD
  image       = var.server_image
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.dentalos.id]
  user_data   = local.cloud_init_base

  # Attach to the private network with a static IP.
  # Static IPs prevent re-configuration after server replacement.
  network {
    network_id = hcloud_network.main.id
    ip         = "10.0.1.10"
    alias_ips  = []
  }

  firewall_ids = [hcloud_firewall.app.id]

  labels = {
    project     = "dentalos"
    environment = var.environment
    role        = "app"
    index       = "1"
  }

  # Ensure the network is ready before attaching the server.
  depends_on = [
    hcloud_network_subnet.app,
  ]

  lifecycle {
    # Prevent accidental replacement of running production servers.
    # To change server_type, resize via Hetzner console and import new state.
    prevent_destroy = false  # Set to true once in stable production

    # Ignore cloud-init changes after initial provisioning.
    ignore_changes = [user_data]
  }
}

# ── App Server 2 ──────────────────────────────────────────────────────────────
# Secondary application server. Identical configuration to app1.
# Blue-green deployments target each server independently.

resource "hcloud_server" "app2" {
  name        = "dentalos-app2"
  server_type = "cx41"
  image       = var.server_image
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.dentalos.id]
  user_data   = local.cloud_init_base

  network {
    network_id = hcloud_network.main.id
    ip         = "10.0.1.11"
    alias_ips  = []
  }

  firewall_ids = [hcloud_firewall.app.id]

  labels = {
    project     = "dentalos"
    environment = var.environment
    role        = "app"
    index       = "2"
  }

  depends_on = [
    hcloud_network_subnet.app,
  ]

  lifecycle {
    prevent_destroy = false
    ignore_changes  = [user_data]
  }
}

# ── Worker Server ─────────────────────────────────────────────────────────────
# Runs RabbitMQ broker + all worker processes (notifications, PDF, DIAN, etc.).
# See deployment-architecture.md §3 for the full worker process list.
# CPX31 = AMD EPYC, better for CPU-bound PDF generation and RIPS export.

resource "hcloud_server" "worker" {
  name        = "dentalos-worker"
  server_type = "cpx31"         # 4 vCPU (AMD), 8 GB RAM, 160 GB SSD
  image       = var.server_image
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.dentalos.id]
  user_data   = local.cloud_init_base

  network {
    network_id = hcloud_network.main.id
    ip         = "10.0.1.20"
    alias_ips  = []
  }

  firewall_ids = [hcloud_firewall.internal.id]

  labels = {
    project     = "dentalos"
    environment = var.environment
    role        = "worker"
  }

  depends_on = [
    hcloud_network_subnet.app,
  ]

  lifecycle {
    prevent_destroy = false
    ignore_changes  = [user_data]
  }
}

# ── Redis Server ──────────────────────────────────────────────────────────────
# Dedicated Redis 7 node for sessions, caching, and permission lookups.
# CX21 is sufficient: Redis is single-threaded and memory-bound.
# If load grows, upgrade to Hetzner Managed Redis (€15/month) for HA.
#
# Redis is a performance enhancement, not a hard dependency — the app falls
# back to PostgreSQL if Redis is unavailable (see caching-strategy.md).

resource "hcloud_server" "redis" {
  name        = "dentalos-redis"
  server_type = "cx21"          # 2 vCPU, 4 GB RAM, 40 GB SSD
  image       = var.server_image
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.dentalos.id]
  user_data   = local.cloud_init_base

  network {
    network_id = hcloud_network.main.id
    ip         = "10.0.1.30"
    alias_ips  = []
  }

  firewall_ids = [hcloud_firewall.internal.id]

  labels = {
    project     = "dentalos"
    environment = var.environment
    role        = "redis"
  }

  depends_on = [
    hcloud_network_subnet.app,
  ]

  lifecycle {
    prevent_destroy = false
    ignore_changes  = [user_data]
  }
}
