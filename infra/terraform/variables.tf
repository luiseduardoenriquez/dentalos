# ─────────────────────────────────────────────────────────────────────────────
# DentalOS — Input Variables
#
# Populate values in terraform.tfvars (gitignored).
# Sensitive variables MUST NOT appear in source control.
# ─────────────────────────────────────────────────────────────────────────────

# ── Authentication ────────────────────────────────────────────────────────────

variable "hcloud_token" {
  description = "Hetzner Cloud API token. Generate at https://console.hetzner.cloud → Project → API Tokens → Read+Write."
  type        = string
  sensitive   = true
}

# ── SSH Access ────────────────────────────────────────────────────────────────

variable "ssh_public_key_path" {
  description = "Path to the SSH public key uploaded to Hetzner and injected into every server."
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

# ── Environment ───────────────────────────────────────────────────────────────

variable "environment" {
  description = "Deployment environment tag applied to all resources. Drives naming and can gate environment-specific behaviour in user_data scripts."
  type        = string
  default     = "production"

  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "environment must be one of: production, staging, development."
  }
}

# ── Region ────────────────────────────────────────────────────────────────────

variable "location" {
  description = "Hetzner datacenter location. FSN1 (Falkenstein) chosen for lower latency to Colombia/LATAM via European peering."
  type        = string
  default     = "fsn1"

  validation {
    condition     = contains(["fsn1", "nbg1", "hel1", "ash", "hil", "sin"], var.location)
    error_message = "location must be a valid Hetzner datacenter code."
  }
}

# ── Domain ────────────────────────────────────────────────────────────────────

variable "domain" {
  description = "Primary domain used for SSL certificate subjects and DNS records."
  type        = string
  default     = "dentalos.co"
}

# ── Database Credentials ──────────────────────────────────────────────────────

variable "postgres_password" {
  description = "Password for the PostgreSQL superuser/application user. Min 32 chars, use a password manager."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.postgres_password) >= 20
    error_message = "postgres_password must be at least 20 characters."
  }
}

# ── Cache Credentials ─────────────────────────────────────────────────────────

variable "redis_password" {
  description = "Redis AUTH password injected into cloud-init and the backend .env. Min 20 chars."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.redis_password) >= 20
    error_message = "redis_password must be at least 20 characters."
  }
}

# ── Queue Credentials ─────────────────────────────────────────────────────────

variable "rabbitmq_password" {
  description = "RabbitMQ admin and app-user password. Min 20 chars."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.rabbitmq_password) >= 20
    error_message = "rabbitmq_password must be at least 20 characters."
  }
}

# ── Image ─────────────────────────────────────────────────────────────────────

variable "server_image" {
  description = "Hetzner server image for all nodes. Ubuntu LTS is the supported base."
  type        = string
  default     = "ubuntu-24.04"
}
