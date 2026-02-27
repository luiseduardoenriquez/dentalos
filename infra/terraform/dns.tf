# ─────────────────────────────────────────────────────────────────────────────
# DentalOS — DNS Records
#
# DNS PROVIDER CHOICE:
#   This file uses Hetzner DNS (dns.hetzner.com) for simplicity.
#   If you use Cloudflare (recommended for DDoS protection + analytics),
#   see the commented-out Cloudflare alternative at the bottom of this file.
#
# To use Hetzner DNS:
#   1. Add 'hetznerdns' provider in required_providers (see comment below)
#   2. Set HETZNER_DNS_TOKEN in your environment or terraform.tfvars
#   3. Uncomment the Hetzner DNS resources below
#
# To use Cloudflare DNS instead:
#   1. Add 'cloudflare' provider in required_providers
#   2. Set cloudflare_api_token variable
#   3. Uncomment the Cloudflare resources at the bottom of this file
#   4. Comment out the Hetzner DNS resources
#
# IMPORTANT: The SSL certificate provisioned in loadbalancer.tf requires DNS
# A records to point to the LB public IP BEFORE it can be issued.
# Run 'terraform apply -target=hcloud_load_balancer.main' first, note the
# LB IP from outputs, add DNS records manually, then run full 'terraform apply'.
# ─────────────────────────────────────────────────────────────────────────────

# ── OPTION A: Hetzner DNS ─────────────────────────────────────────────────────
# Uncomment if using Hetzner DNS. Also add to required_providers in main.tf:
#   hetznerdns = {
#     source  = "timohirt/hetznerdns"
#     version = "~> 2.2"
#   }
# And add to provider block:
#   provider "hetznerdns" {
#     apitoken = var.hetzner_dns_token
#   }

# data "hetznerdns_zone" "main" {
#   name = var.domain
# }
#
# # A record: dentalos.co → LB public IP
# resource "hetznerdns_record" "apex" {
#   zone_id = data.hetznerdns_zone.main.id
#   name    = "@"
#   type    = "A"
#   value   = hcloud_load_balancer.main.ipv4
#   ttl     = 300
# }
#
# # A record: api.dentalos.co → LB public IP (FastAPI on port 8443)
# resource "hetznerdns_record" "api" {
#   zone_id = data.hetznerdns_zone.main.id
#   name    = "api"
#   type    = "A"
#   value   = hcloud_load_balancer.main.ipv4
#   ttl     = 300
# }
#
# # CNAME: www.dentalos.co → dentalos.co
# resource "hetznerdns_record" "www" {
#   zone_id = data.hetznerdns_zone.main.id
#   name    = "www"
#   type    = "CNAME"
#   value   = "${var.domain}."   # Trailing dot = fully qualified
#   ttl     = 300
# }
#
# # AAAA record: dentalos.co → LB IPv6 (Hetzner provides both)
# resource "hetznerdns_record" "apex_ipv6" {
#   zone_id = data.hetznerdns_zone.main.id
#   name    = "@"
#   type    = "AAAA"
#   value   = hcloud_load_balancer.main.ipv6
#   ttl     = 300
# }
#
# # MX record: point to your email provider (update value as needed)
# # resource "hetznerdns_record" "mx" {
# #   zone_id  = data.hetznerdns_zone.main.id
# #   name     = "@"
# #   type     = "MX"
# #   value    = "10 mail.dentalos.co."
# #   ttl      = 3600
# # }
#
# # TXT record: SPF for transactional email (update with your provider)
# # resource "hetznerdns_record" "spf" {
# #   zone_id = data.hetznerdns_zone.main.id
# #   name    = "@"
# #   type    = "TXT"
# #   value   = "\"v=spf1 include:amazonses.com ~all\""
# #   ttl     = 3600
# # }

# ── OPTION B: Cloudflare DNS (recommended) ────────────────────────────────────
# Cloudflare provides: DDoS protection, WAF, analytics, CDN, 0ms TTL changes.
# For a SaaS handling PHI, Cloudflare's WAF and rate limiting add meaningful
# security depth. The free tier is sufficient for DentalOS MVP.
#
# Add to required_providers in main.tf:
#   cloudflare = {
#     source  = "cloudflare/cloudflare"
#     version = "~> 4.0"
#   }
#
# Add variable (in variables.tf):
#   variable "cloudflare_api_token" {
#     type      = string
#     sensitive = true
#   }
#   variable "cloudflare_zone_id" {
#     type = string
#     description = "Cloudflare Zone ID for the domain (from Cloudflare dashboard)"
#   }
#
# provider "cloudflare" {
#   api_token = var.cloudflare_api_token
# }
#
# IMPORTANT: When using Cloudflare proxy (orange cloud), set SSL/TLS mode to
# "Full (strict)" in Cloudflare dashboard. The Hetzner managed cert handles
# Hetzner↔server TLS; Cloudflare handles browser↔Cloudflare TLS.
#
# resource "cloudflare_record" "apex" {
#   zone_id = var.cloudflare_zone_id
#   name    = "@"
#   type    = "A"
#   value   = hcloud_load_balancer.main.ipv4
#   proxied = true    # Orange cloud ON — DDoS + WAF + CDN
#   ttl     = 1       # Auto TTL when proxied
# }
#
# resource "cloudflare_record" "api" {
#   zone_id = var.cloudflare_zone_id
#   name    = "api"
#   type    = "A"
#   value   = hcloud_load_balancer.main.ipv4
#   proxied = true
#   ttl     = 1
# }
#
# resource "cloudflare_record" "www" {
#   zone_id = var.cloudflare_zone_id
#   name    = "www"
#   type    = "CNAME"
#   value   = var.domain
#   proxied = true
#   ttl     = 1
# }
#
# resource "cloudflare_record" "apex_ipv6" {
#   zone_id = var.cloudflare_zone_id
#   name    = "@"
#   type    = "AAAA"
#   value   = hcloud_load_balancer.main.ipv6
#   proxied = true
#   ttl     = 1
# }

# ── Placeholder output ────────────────────────────────────────────────────────
# DNS management is manual until one of the above options is uncommented.
# After applying, configure DNS manually or via the Hetzner/Cloudflare console:
#
#   A     dentalos.co         → <lb_ipv4>   (see: terraform output lb_ipv4)
#   A     api.dentalos.co     → <lb_ipv4>
#   CNAME www.dentalos.co     → dentalos.co
#   AAAA  dentalos.co         → <lb_ipv6>   (see: terraform output lb_ipv6)
