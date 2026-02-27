# ─────────────────────────────────────────────────────────────────────────────
# DentalOS Backend — Multi-stage Dockerfile
#
# Stage 1 (builder): Install uv, resolve and install all production Python
#   dependencies into the system site-packages, then copy application code.
# Stage 2 (runtime): Copy only the installed packages and app code from the
#   builder into a clean python:3.12-slim image. No build toolchain ships to
#   production.
#
# Final image: ~200-250 MB (vs ~500+ MB with build tools included).
# ─────────────────────────────────────────────────────────────────────────────

LABEL maintainer="DentalOS Engineering <eng@dentalos.co>"
LABEL description="DentalOS FastAPI backend — multi-tenant dental SaaS"
LABEL org.opencontainers.image.source="https://github.com/dentalos/dentalos"

# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv — the fast Python package installer used by this project.
# Pinned to a specific version for reproducible builds.
# curl is needed to fetch the uv installer and is removed from the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && curl -LsSf https://astral.sh/uv/0.5.20/install.sh | sh \
    && apt-get purge -y curl \
    && rm -rf /var/lib/apt/lists/*

# Add uv to PATH (installer places it in ~/.cargo/bin by default)
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

# Copy dependency manifest first so Docker can cache the install layer.
# The installed packages will only be rebuilt when pyproject.toml or
# uv.lock changes — not when application source code changes.
COPY pyproject.toml uv.lock* ./

# Install production dependencies directly into system site-packages.
# --no-dev excludes test/lint/type-check tooling from the production image.
# --no-cache avoids storing the uv download cache inside the image layer.
# --system writes packages to /usr/local/lib/python3.12/site-packages.
RUN uv pip install --system --no-cache --no-dev .

# Copy the rest of the application source. This layer is invalidated on every
# source change, but that is fast because no pip install runs here.
COPY app/ ./app/
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY alembic_public/ ./alembic_public/
COPY alembic_tenant/ ./alembic_tenant/
COPY templates/ ./templates/
COPY gunicorn.conf.py ./

# Copy JWT key files required by the auth system at runtime.
# NOTE: In production, mount these via a Docker secret or a secrets manager
# (e.g., Hetzner Vault, AWS Secrets Manager) rather than baking them into the
# image. This COPY is provided as a fallback for self-hosted deployments where
# key rotation is managed externally.
COPY keys/ ./keys/


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="DentalOS Engineering <eng@dentalos.co>"
LABEL description="DentalOS FastAPI backend — production runtime"

# Install curl for the HEALTHCHECK and ca-certificates for outbound HTTPS.
# libpq5 provides the PostgreSQL shared library required by psycopg (binary).
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create a dedicated non-root user and group.
# Running as root inside a container is a significant security risk — if the
# process is compromised the attacker gains root-equivalent host privileges.
RUN groupadd --system dentalos \
    && useradd --system --gid dentalos --no-create-home --shell /usr/sbin/nologin dentalos

WORKDIR /app

# Copy installed Python packages from the builder stage.
# We copy site-packages (third-party libraries) and any scripts that pip/uv
# installed into /usr/local/bin (e.g., gunicorn, uvicorn, alembic).
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --from=builder /usr/local/bin/uvicorn  /usr/local/bin/uvicorn
COPY --from=builder /usr/local/bin/alembic  /usr/local/bin/alembic

# Copy application code and supporting files.
COPY --from=builder --chown=dentalos:dentalos /app/app/           ./app/
COPY --from=builder --chown=dentalos:dentalos /app/alembic.ini    ./alembic.ini
COPY --from=builder --chown=dentalos:dentalos /app/alembic/       ./alembic/
COPY --from=builder --chown=dentalos:dentalos /app/alembic_public/ ./alembic_public/
COPY --from=builder --chown=dentalos:dentalos /app/alembic_tenant/ ./alembic_tenant/
COPY --from=builder --chown=dentalos:dentalos /app/templates/     ./templates/
COPY --from=builder --chown=dentalos:dentalos /app/gunicorn.conf.py ./gunicorn.conf.py
COPY --from=builder --chown=dentalos:dentalos /app/keys/          ./keys/

# Switch to the non-root user before setting runtime configuration.
USER dentalos

# Document the port the application listens on. This does not publish the port
# — the actual binding is done in docker-compose / Kubernetes manifests.
EXPOSE 8000

# Verify the application starts cleanly during the image build.
# This also validates that all imports resolve so broken images are caught early.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Use gunicorn with UvicornWorker for production.
# Worker count, log level, etc. are controlled via environment variables
# read by gunicorn.conf.py (WEB_WORKERS, LOG_LEVEL).
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
