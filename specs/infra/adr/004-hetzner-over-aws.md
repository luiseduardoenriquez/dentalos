# ADR-004: Hetzner Cloud over AWS/GCP

**Status:** Accepted
**Date:** 2026-02-24
**Authors:** DentalOS Architecture Team

---

## Context

DentalOS targets dental practices in Latin America, a price-sensitive market where
solo practitioners and small clinics (1-5 chairs) represent the majority of potential
customers. The freemium pricing model offers a free tier ($0/month for a single
practitioner) and a paid tier at $69/location/month. Infrastructure cost directly
impacts two critical business metrics:

1. **Free tier viability**: If infrastructure costs $1,000+/month before the first
   paying customer, the freemium model fails.
2. **Gross margin on paid tier**: At $69/location/month, infrastructure cost per
   tenant must remain well below $5/month to achieve healthy SaaS margins (>75%).

### Infrastructure Requirements

The MVP deployment requires: compute (FastAPI + Uvicorn, 4 vCPU / 16 GB RAM),
managed PostgreSQL 16+ (per [ADR-003](003-postgresql-over-alternatives.md)),
S3-compatible object storage (consent forms, radiographic images, ~100 GB year one),
load balancer (TLS termination, HTTP/2), RabbitMQ (async tasks), Redis (caching,
rate limiting), and monitoring (Prometheus + Grafana).

### Latency Requirements

Target users are in Colombia, Mexico, Chile, Argentina, and Peru.

| City | Latency (Ashburn) | Latency (Sao Paulo) |
|------|-------------------|---------------------|
| Bogota, Colombia | ~55ms | ~120ms |
| Mexico City, Mexico | ~45ms | ~160ms |
| Santiago, Chile | ~90ms | ~40ms |
| Buenos Aires, Argentina | ~110ms | ~35ms |
| Lima, Peru | ~75ms | ~95ms |

Ashburn provides the best average latency across all five target countries,
with no city exceeding 120ms network round-trip.

## Decision

We will host DentalOS on **Hetzner Cloud** using the **Ashburn (US-East) data
center** for the initial deployment.

### Infrastructure Configuration

| Component | Hetzner Product | Specification | Monthly Cost |
|-----------|----------------|---------------|-------------|
| App server 1 | CPX31 | 4 vCPU, 8 GB RAM, 160 GB NVMe | $15.59 |
| App server 2 | CPX31 | 4 vCPU, 8 GB RAM, 160 GB NVMe | $15.59 |
| Managed PostgreSQL | Primary + replica | 4 vCPU, 16 GB RAM, 200 GB | $49.00 |
| Load balancer | LB11 | 25 concurrent connections | $6.49 |
| Object storage | S3-compatible | 100 GB + transfer | ~$5.00 |
| Volumes (backups) | Block storage | 100 GB | $4.80 |
| **Total** | | | **~$96.47** |

Self-managed components (Docker on app servers): RabbitMQ, Redis, Prometheus +
Grafana. **Total estimated monthly cost: ~$100-150/month** including bandwidth.

### Scaling Path

Beyond 500 tenants: vertical scaling (CPX41, 8 vCPU), horizontal app servers,
dedicated RabbitMQ/Redis instances, PostgreSQL upgrades with read replicas. The
architecture remains on Hetzner until ~5,000+ tenants or multi-region requirements.

## Alternatives Considered

### Alternative 1: Amazon Web Services (AWS)

| Component | AWS Product | Specification | Monthly Cost |
|-----------|------------|---------------|-------------|
| App server 1 | EC2 t3.xlarge | 4 vCPU, 16 GB RAM | $121.47 |
| App server 2 | EC2 t3.xlarge | 4 vCPU, 16 GB RAM | $121.47 |
| Managed PostgreSQL | RDS db.t3.xlarge | 4 vCPU, 16 GB, 200 GB gp3 | $285.00 |
| Load balancer | ALB | Standard | $22.00 |
| Object storage | S3 | 100 GB Standard | $2.30 |
| Redis | ElastiCache t3.micro | 1 node | $12.24 |
| RabbitMQ | Amazon MQ mq.t3.micro | Single-instance | $21.00 |
| Data transfer | Outbound | ~50 GB/month | $4.50 |
| **Total** | | | **~$590.00** |

**Why not chosen:** 4-6x more expensive ($590 on-demand, ~$410 reserved). Hidden
costs (AZ transfer, NAT gateway, CloudWatch ingestion, RDS IOPS). Managed services
breadth (Lambda, SQS, Cognito) is overkill for MVP.

**Trade-offs if chosen:** Fully managed stack reduces operations. Sao Paulo data
center for southern LATAM latency. HIPAA BAAs if expanding to US market.

### Alternative 2: Google Cloud Platform (GCP)

| Component | GCP Product | Specification | Monthly Cost |
|-----------|------------|---------------|-------------|
| App servers (2x) | e2-standard-4 | 4 vCPU, 16 GB RAM each | $195.66 |
| Managed PostgreSQL | Cloud SQL db-standard-4 | 4 vCPU, 16 GB, 200 GB SSD | $260.00 |
| Load balancer | Cloud LB | Standard | $18.00 |
| Object storage | Cloud Storage | 100 GB Standard | $2.60 |
| Redis | Memorystore Basic M1 | 1 GB | $35.00 |
| **Total** | | | **~$517.00** |

**Why not chosen:** 3.5-5x more expensive. No LATAM data centers beyond Sao Paulo.
GCP strengths (BigQuery, Vertex AI, Spanner) are irrelevant for MVP.

**Trade-offs if chosen:** Cloud Run for serverless scaling. Good IAM integration.

### Alternative 3: DigitalOcean

| Component | DO Product | Specification | Monthly Cost |
|-----------|-----------|---------------|-------------|
| App servers (2x) | Premium Droplet | 4 vCPU, 8 GB RAM each | $96.00 |
| Managed PostgreSQL | DB cluster | 4 vCPU, 8 GB RAM, 115 GB | $100.00 |
| Load balancer | DO LB | Standard | $12.00 |
| Object storage | Spaces | 250 GB | $5.00 |
| Redis | Managed Redis | 1 GB | $15.00 |
| **Total** | | | **~$228.00** |

**Why not chosen:** 2x Hetzner's cost. PostgreSQL extension limitations on some
plans. Less RAM per dollar.

**Trade-offs if chosen:** Larger community, managed Kubernetes, GitHub auto-deploy.

### Cost Comparison Summary

| Provider | Monthly Cost | vs Hetzner | Managed Services |
|----------|-------------|------------|-----------------|
| **Hetzner** | **~$100-150** | **baseline** | PostgreSQL, S3, LB |
| DigitalOcean | ~$228 | 1.5-2.3x | PostgreSQL, Redis, S3, LB |
| GCP | ~$517 | 3.4-5.2x | Full managed stack |
| AWS | ~$590 | 3.9-5.9x | Full managed stack |

## Consequences

### Positive

- **4-6x cost savings**: MVP infrastructure under $150/month, making the freemium
  model viable from day one. At 2,000 tenants, cost per tenant is ~$0.075/month.
- **Predictable pricing**: Flat monthly rates with 20 TB/month bandwidth included.
  No surprise bills from data transfer or API call fees.
- **Sufficient managed services**: Managed PostgreSQL, S3-compatible storage, and
  load balancing cover the highest-operational-burden components.
- **Performance per dollar**: AMD EPYC processors with NVMe storage deliver
  benchmark performance comparable to AWS t3/m5 at a fraction of the cost.

### Negative

- **Smaller managed service ecosystem**: No managed RabbitMQ, Redis, or Kubernetes.
  Self-managed via Docker, accepting operational responsibility for updates and
  monitoring.
- **No LATAM data center**: Ashburn latency is acceptable (45-120ms to target
  cities) but a Bogota/Sao Paulo data center would save 40-60ms for some users.
  Evaluate CDN/edge caching if latency becomes competitive issue.
- **Smaller community**: Less provider-specific documentation. Relies on generic
  Linux/PostgreSQL/Docker knowledge for debugging.
- **No healthcare compliance certifications**: ISO 27001 but no HIPAA BAAs. Acceptable
  for LATAM regulations; cloud migration needed if expanding to US market.
- **Limited IAM**: API token-based permissions rather than role-based policies.
  Sufficient for a small team but could limit larger organizations.

### Neutral

- **Docker-based deployment**: Runs identically on any cloud provider. Docker
  Compose for MVP, Docker Swarm or Kubernetes as scale demands.
- **Standard protocols ensure portability**: PostgreSQL, S3 API, AMQP, Redis
  protocol are cloud-agnostic. Migration requires config changes, not code changes.
  Estimated migration effort: 1-2 engineer-weeks.
- **Monitoring self-managed regardless**: Prometheus + Grafana for application
  metrics runs the same on Hetzner as on AWS.
- **DNS and CDN external**: Cloudflare handles DNS, CDN, and DDoS protection
  independently of the hosting provider.

## References

- [`infra/multi-tenancy.md`](../multi-tenancy.md) -- Infrastructure requirements for multi-tenant deployment
- [`infra/database-architecture.md`](../database-architecture.md) -- Managed PostgreSQL hosting configuration
- [`infra/authentication-rules.md`](../authentication-rules.md) -- Auth infrastructure deployment
- [ADR-001: Schema-per-tenant](001-schema-per-tenant.md) -- Multi-tenancy requiring managed PostgreSQL
- [ADR-002: FastAPI over Django](002-fastapi-over-django.md) -- Application framework deployed on Hetzner compute
- [ADR-003: PostgreSQL over alternatives](003-postgresql-over-alternatives.md) -- Database hosted on Hetzner managed PostgreSQL
- [Hetzner Cloud Pricing](https://www.hetzner.com/cloud/)
- [Hetzner Managed Databases](https://www.hetzner.com/cloud/managed-database)
- [Hetzner Object Storage](https://www.hetzner.com/cloud/object-storage)
- [AWS EC2 Pricing](https://aws.amazon.com/ec2/pricing/)
- [AWS RDS Pricing](https://aws.amazon.com/rds/pricing/)
- [GCP Compute Engine Pricing](https://cloud.google.com/compute/pricing)
- [DigitalOcean Pricing](https://www.digitalocean.com/pricing)
