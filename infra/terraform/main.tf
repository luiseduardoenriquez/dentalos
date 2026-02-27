# ─────────────────────────────────────────────────────────────────────────────
# DentalOS — Terraform Root Configuration
#
# Provider:    Hetzner Cloud (hcloud)
# State:       Local (see comment below for remote state migration)
# Region:      Falkenstein (fsn1), Germany
# Estimated:   ~€78/month at full topology
#
# Usage:
#   terraform init
#   terraform plan -var-file="terraform.tfvars"
#   terraform apply -var-file="terraform.tfvars"
# ─────────────────────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.47"
    }
  }

  # LOCAL STATE — works for a solo operator or small team.
  # Before inviting additional engineers, migrate to a shared remote backend:
  #
  # backend "s3" {
  #   bucket                      = "dentalos-terraform-state"
  #   key                         = "production/terraform.tfstate"
  #   region                      = "eu-central-1"
  #   # For Hetzner Object Storage (S3-compatible):
  #   endpoint                    = "https://fsn1.your-objectstorage.com"
  #   skip_credentials_validation = true
  #   skip_metadata_api_check     = true
  #   skip_region_validation      = true
  #   force_path_style            = true
  #   encrypt                     = true
  # }
  #
  # State locking via DynamoDB (AWS) or native Hetzner Object Storage versioning.
}

# ── Hetzner Cloud Provider ────────────────────────────────────────────────────
# The token is read from the variable (never hardcoded here).
# Export HCLOUD_TOKEN in CI, or pass via terraform.tfvars (gitignored).
provider "hcloud" {
  token = var.hcloud_token
}
