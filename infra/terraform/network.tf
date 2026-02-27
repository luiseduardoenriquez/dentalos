# ─────────────────────────────────────────────────────────────────────────────
# DentalOS — Network Resources
#
# Topology:
#   Private Network:  10.0.0.0/16  (all internal traffic)
#   App Subnet:       10.0.1.0/24  (servers + LB targets)
#
# Firewall policy: default-deny inbound. Only 80/443 public, 22 restricted,
# and all traffic within the private network is allowed.
# ─────────────────────────────────────────────────────────────────────────────

# ── Private Network ───────────────────────────────────────────────────────────
# Hetzner private networks are L2-isolated per project. All servers are
# attached here so inter-service traffic never leaves Hetzner's internal
# switching fabric — no public bandwidth consumed, no encryption overhead.

resource "hcloud_network" "main" {
  name     = "dentalos-private-network"
  ip_range = "10.0.0.0/16"

  labels = {
    project     = "dentalos"
    environment = var.environment
  }
}

# ── App Subnet ────────────────────────────────────────────────────────────────
# Single /24 subnet is plenty for the current topology.
# Reserve 10.0.2.0/24 for a future worker/jobs subnet if you split the
# worker server out to its own subnet for stricter firewall segmentation.

resource "hcloud_network_subnet" "app" {
  network_id   = hcloud_network.main.id
  type         = "cloud"
  network_zone = "eu-central"   # Matches fsn1 / nbg1 / hel1
  ip_range     = "10.0.1.0/24"
}

# ── App Server Firewall ───────────────────────────────────────────────────────
# Applied to app1, app2. The load balancer forwards inbound; servers should
# only accept traffic from the LB and the private network.
#
# IMPORTANT: In production, restrict SSH (port 22) to your ops/bastion IP.
# Replace 0.0.0.0/0 / ::/0 on the SSH rule with your actual IP ranges.

resource "hcloud_firewall" "app" {
  name = "dentalos-app-firewall"

  labels = {
    project     = "dentalos"
    environment = var.environment
    tier        = "app"
  }

  # SSH — restrict to your ops IPs in production.
  # Using 0.0.0.0/0 here is intentional during initial bootstrap so you can
  # access the servers before the bastion host is configured. Tighten after.
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
    description = "SSH — RESTRICT TO OPS IPs IN PRODUCTION"
  }

  # HTTP — Hetzner LB forwards health checks and redirect traffic
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
    description = "HTTP from LB and internet (nginx handles redirect)"
  }

  # HTTPS — primary traffic entry point
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
    description = "HTTPS from LB"
  }

  # FastAPI — LB forwards to this port, also used by private-network services
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "8000"
    source_ips = ["10.0.0.0/16"]
    description = "FastAPI — private network only"
  }

  # Next.js — LB forwards to this port
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "3000"
    source_ips = ["10.0.0.0/16"]
    description = "Next.js SSR — private network only"
  }

  # ICMP — required for LB health probes and network diagnostics
  rule {
    direction  = "in"
    protocol   = "icmp"
    source_ips = ["0.0.0.0/0", "::/0"]
    description = "ICMP ping"
  }

  # Private network — allow all inbound from within 10.0.0.0/16
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "any"
    source_ips = ["10.0.0.0/16"]
    description = "All TCP from private network"
  }
}

# ── Worker/DB/Redis Firewall ──────────────────────────────────────────────────
# Applied to the worker, DB, and Redis servers.
# These nodes have no public-facing services. The only inbound allowed is
# SSH (for ops) and full TCP within the private network.

resource "hcloud_firewall" "internal" {
  name = "dentalos-internal-firewall"

  labels = {
    project     = "dentalos"
    environment = var.environment
    tier        = "internal"
  }

  # SSH — same note as above: lock down to your ops IP in production
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
    description = "SSH — RESTRICT TO OPS IPs IN PRODUCTION"
  }

  # All TCP from private network (PostgreSQL 5432, Redis 6379, AMQP 5672, etc.)
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "any"
    source_ips = ["10.0.0.0/16"]
    description = "All TCP from private network"
  }

  # ICMP
  rule {
    direction  = "in"
    protocol   = "icmp"
    source_ips = ["10.0.0.0/16"]
    description = "ICMP from private network"
  }
}
