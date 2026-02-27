# ─────────────────────────────────────────────────────────────────────────────
# DentalOS — Load Balancer
#
# Hetzner LB11: entry-level load balancer, sufficient for early production.
#   - 1,000 concurrent connections
#   - 20,000 requests/second
#   - SSL termination (Let's Encrypt managed certificate)
#   - Cost: ~€6/month
#
# Traffic flow:
#   Internet → LB (443 HTTPS) → app servers (:3000 frontend, :8000 backend)
#   Internet → LB (80 HTTP)   → redirect 301 → HTTPS
#
# The LB targets BOTH app servers in round-robin. Health checks remove a
# server from rotation within 45 seconds (3 failures × 15s interval).
# ─────────────────────────────────────────────────────────────────────────────

# ── Load Balancer ─────────────────────────────────────────────────────────────

resource "hcloud_load_balancer" "main" {
  name               = "dentalos-lb"
  load_balancer_type = "lb11"
  location           = var.location
  algorithm {
    type = "round_robin"
  }

  labels = {
    project     = "dentalos"
    environment = var.environment
  }
}

# ── Private Network Attachment ────────────────────────────────────────────────
# The LB communicates with app servers over the private network.
# Backends must listen on their private IPs, not 0.0.0.0.

resource "hcloud_load_balancer_network" "main" {
  load_balancer_id        = hcloud_load_balancer.main.id
  network_id              = hcloud_network.main.id
  ip                      = "10.0.1.5"   # Static private IP for the LB itself
  enable_public_interface = true          # LB still needs a public IP for internet traffic
}

# ── SSL Certificate ───────────────────────────────────────────────────────────
# Hetzner managed certificates auto-renew via Let's Encrypt.
# No certbot required on the servers — renewal is handled by Hetzner.
# DNS validation requires the domain's A record to point to the LB public IP
# BEFORE running `terraform apply` with this resource.
#
# Domains covered:
#   dentalos.co         → main app
#   www.dentalos.co     → redirect to dentalos.co
#   api.dentalos.co     → FastAPI backend (direct API access)
#
# If you use Cloudflare as DNS: set SSL/TLS mode to "Full (strict)" and
# disable the Cloudflare proxy (orange cloud) until the cert is issued.

resource "hcloud_managed_certificate" "main" {
  name = "dentalos-ssl"

  domain_names = [
    var.domain,
    "www.${var.domain}",
    "api.${var.domain}",
  ]

  labels = {
    project     = "dentalos"
    environment = var.environment
  }
}

# ── Frontend Service (HTTPS → :3000) ─────────────────────────────────────────
# Handles all non-API traffic. Next.js listens on port 3000.
# The LB terminates SSL and forwards plain HTTP to the backend servers.

resource "hcloud_load_balancer_service" "https_frontend" {
  load_balancer_id = hcloud_load_balancer.main.id
  protocol         = "https"
  listen_port      = 443
  destination_port = 3000
  proxyprotocol    = true           # Passes client IP to Next.js via PROXY protocol

  http {
    # Redirect HTTP to HTTPS is handled by the http_redirect service below.
    sticky_sessions = false         # Next.js is stateless; sessions live in JWT
    certificates    = [hcloud_managed_certificate.main.id]
  }

  health_check {
    protocol = "http"
    port     = 3000
    interval = 15        # seconds between probes
    timeout  = 10        # probe timeout
    retries  = 3         # failures before removal from rotation

    http {
      path         = "/"           # Next.js root page
      status_codes = ["2??", "3??"] # Accept 2xx and 3xx as healthy
    }
  }
}

# ── Backend API Service (HTTPS → :8000) ───────────────────────────────────────
# A second HTTPS listener on port 8443 exposes the FastAPI backend directly.
# This allows api.dentalos.co to reach the API without routing through Next.js.
# Mobile apps and third-party integrations use this endpoint.
#
# Alternative: Route /api/* via the frontend LB service and let Next.js
# proxy to the backend. Chose direct exposure to avoid extra hop latency.

resource "hcloud_load_balancer_service" "https_backend" {
  load_balancer_id = hcloud_load_balancer.main.id
  protocol         = "https"
  listen_port      = 8443
  destination_port = 8000
  proxyprotocol    = true

  http {
    sticky_sessions = false
    certificates    = [hcloud_managed_certificate.main.id]
  }

  health_check {
    protocol = "http"
    port     = 8000
    interval = 15
    timeout  = 10
    retries  = 3

    http {
      path         = "/api/v1/health"  # FastAPI health endpoint
      status_codes = ["200"]
    }
  }
}

# ── HTTP Redirect Service (80 → HTTPS) ────────────────────────────────────────
# Hetzner LB can redirect HTTP to HTTPS natively. All port-80 traffic
# is answered with a 301 redirect to https://<same-host><same-path>.

resource "hcloud_load_balancer_service" "http_redirect" {
  load_balancer_id = hcloud_load_balancer.main.id
  protocol         = "http"
  listen_port      = 80
  destination_port = 443   # Redirected by Hetzner, not forwarded

  http {
    redirect_http = true   # Hetzner-native HTTP → HTTPS redirect
  }

  # No health check needed — redirect never hits backends.
}

# ── Load Balancer Targets ─────────────────────────────────────────────────────
# Both app servers are registered as targets. Hetzner LB uses the private
# network to reach them on the configured destination ports.

resource "hcloud_load_balancer_target" "app1" {
  type             = "server"
  load_balancer_id = hcloud_load_balancer.main.id
  server_id        = hcloud_server.app1.id
  use_private_ip   = true        # Prefer private network to avoid public traffic costs

  depends_on = [hcloud_load_balancer_network.main]
}

resource "hcloud_load_balancer_target" "app2" {
  type             = "server"
  load_balancer_id = hcloud_load_balancer.main.id
  server_id        = hcloud_server.app2.id
  use_private_ip   = true

  depends_on = [hcloud_load_balancer_network.main]
}
