# ─────────────────────────────────────────────────────────────────────────────
# DentalOS — Terraform Outputs
#
# Run after apply:  terraform output
# Specific value:   terraform output -raw lb_ipv4
# JSON all:         terraform output -json
#
# Sensitive outputs (passwords) are masked by default.
# To view: terraform output -raw <name>
# ─────────────────────────────────────────────────────────────────────────────

# ── Load Balancer ─────────────────────────────────────────────────────────────

output "lb_ipv4" {
  description = "Load balancer public IPv4. Point your DNS A records here."
  value       = hcloud_load_balancer.main.ipv4
}

output "lb_ipv6" {
  description = "Load balancer public IPv6. Point your DNS AAAA records here."
  value       = hcloud_load_balancer.main.ipv6
}

output "lb_id" {
  description = "Hetzner internal load balancer ID. Used when configuring targets via hcloud CLI."
  value       = hcloud_load_balancer.main.id
}

# ── App Servers ───────────────────────────────────────────────────────────────

output "app1_public_ip" {
  description = "App server 1 public IPv4. Use for direct SSH access."
  value       = hcloud_server.app1.ipv4_address
}

output "app1_private_ip" {
  description = "App server 1 private IP (10.0.1.10). Used for internal routing."
  value       = "10.0.1.10"
}

output "app2_public_ip" {
  description = "App server 2 public IPv4."
  value       = hcloud_server.app2.ipv4_address
}

output "app2_private_ip" {
  description = "App server 2 private IP (10.0.1.11)."
  value       = "10.0.1.11"
}

# ── Worker Server ─────────────────────────────────────────────────────────────

output "worker_public_ip" {
  description = "Worker server public IPv4 (RabbitMQ + background workers)."
  value       = hcloud_server.worker.ipv4_address
}

output "worker_private_ip" {
  description = "Worker server private IP (10.0.1.20)."
  value       = "10.0.1.20"
}

# ── Redis Server ──────────────────────────────────────────────────────────────

output "redis_public_ip" {
  description = "Redis server public IPv4 (for SSH only — Redis port is not publicly exposed)."
  value       = hcloud_server.redis.ipv4_address
}

output "redis_private_ip" {
  description = "Redis server private IP (10.0.1.30). Use in REDIS_URL env var."
  value       = "10.0.1.30"
}

# ── Database Server ───────────────────────────────────────────────────────────

output "db_public_ip" {
  description = "DB server public IPv4 (for SSH only — PostgreSQL port is not publicly exposed)."
  value       = hcloud_server.db.ipv4_address
}

output "db_private_ip" {
  description = "DB server private IP (10.0.1.40). Use in DATABASE_URL env var."
  value       = "10.0.1.40"
}

output "db_volume_id" {
  description = "Hetzner volume ID for PostgreSQL data. Do not delete."
  value       = hcloud_volume.db_data.id
}

# ── Connection Commands ───────────────────────────────────────────────────────
# Copy-paste SSH commands for quick access.

output "ssh_app1" {
  description = "SSH command for app server 1."
  value       = "ssh -i ${var.ssh_public_key_path == "~/.ssh/id_rsa.pub" ? "~/.ssh/id_rsa" : trimsuffix(var.ssh_public_key_path, ".pub")} root@${hcloud_server.app1.ipv4_address}"
}

output "ssh_app2" {
  description = "SSH command for app server 2."
  value       = "ssh -i ${var.ssh_public_key_path == "~/.ssh/id_rsa.pub" ? "~/.ssh/id_rsa" : trimsuffix(var.ssh_public_key_path, ".pub")} root@${hcloud_server.app2.ipv4_address}"
}

output "ssh_worker" {
  description = "SSH command for worker server."
  value       = "ssh -i ${var.ssh_public_key_path == "~/.ssh/id_rsa.pub" ? "~/.ssh/id_rsa" : trimsuffix(var.ssh_public_key_path, ".pub")} root@${hcloud_server.worker.ipv4_address}"
}

output "ssh_redis" {
  description = "SSH command for Redis server."
  value       = "ssh -i ${var.ssh_public_key_path == "~/.ssh/id_rsa.pub" ? "~/.ssh/id_rsa" : trimsuffix(var.ssh_public_key_path, ".pub")} root@${hcloud_server.redis.ipv4_address}"
}

output "ssh_db" {
  description = "SSH command for database server."
  value       = "ssh -i ${var.ssh_public_key_path == "~/.ssh/id_rsa.pub" ? "~/.ssh/id_rsa" : trimsuffix(var.ssh_public_key_path, ".pub")} root@${hcloud_server.db.ipv4_address}"
}

# ── Environment Variables Template ────────────────────────────────────────────
# Print the connection strings for the backend .env file.
# Passwords are masked — copy from terraform.tfvars manually.

output "env_database_url" {
  description = "DATABASE_URL value for the backend .env (replace PASSWORD placeholder)."
  value       = "postgresql+asyncpg://dentalos:PASSWORD@10.0.1.40:5432/dentalos"
}

output "env_redis_url" {
  description = "REDIS_URL value for the backend .env (replace PASSWORD placeholder)."
  value       = "redis://:PASSWORD@10.0.1.30:6379/0"
}

output "env_rabbitmq_url" {
  description = "RABBITMQ_URL value for the backend .env (replace PASSWORD placeholder)."
  value       = "amqp://dentalos:PASSWORD@10.0.1.20:5672/dentalos"
}

# ── Network ───────────────────────────────────────────────────────────────────

output "network_id" {
  description = "Hetzner private network ID."
  value       = hcloud_network.main.id
}

output "network_cidr" {
  description = "Private network CIDR range."
  value       = hcloud_network.main.ip_range
}

# ── SSL Certificate ───────────────────────────────────────────────────────────

output "ssl_certificate_id" {
  description = "Hetzner managed SSL certificate ID. Renewal is automatic."
  value       = hcloud_managed_certificate.main.id
}

output "ssl_domains" {
  description = "Domains covered by the SSL certificate."
  value       = hcloud_managed_certificate.main.domain_names
}

# ── Cost Summary ─────────────────────────────────────────────────────────────

output "estimated_monthly_cost_eur" {
  description = "Estimated monthly infrastructure cost breakdown."
  value = {
    app1_cx41         = "€17"
    app2_cx41         = "€17"
    worker_cpx31      = "€13"
    db_cpx31          = "€13"
    redis_cx21        = "€6"
    load_balancer_lb11 = "€6"
    db_volume_40gb    = "€2"
    total_approximate = "€74"
    note              = "Add Hetzner Object Storage (~€5/TB) for S3-compatible MinIO alternative"
  }
}
