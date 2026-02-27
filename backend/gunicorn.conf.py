"""
gunicorn.conf.py — Production Gunicorn configuration for DentalOS backend.

Gunicorn spawns UvicornWorker processes, which run the FastAPI ASGI app with
the full uvicorn event loop (asyncio).  This gives us:
  - Gunicorn's battle-tested process management and graceful restarts
  - Uvicorn's high-performance async I/O for FastAPI/Starlette

Environment variables that tune this config:
  WEB_WORKERS  — number of worker processes (default: 4)
  LOG_LEVEL    — gunicorn log verbosity: debug|info|warning|error|critical
"""

import os

# ── Binding ───────────────────────────────────────────────────────────────────
# Listen on all interfaces inside the container.  The external port mapping is
# handled by Docker / the load balancer, never by gunicorn directly.
bind = "0.0.0.0:8000"

# ── Workers ───────────────────────────────────────────────────────────────────
# Rule of thumb for async workers: 2-4 per CPU core.
# WEB_WORKERS defaults to 4 which suits a 2-core Hetzner CX21 comfortably.
# For memory-constrained environments, set WEB_WORKERS=2.
workers = int(os.getenv("WEB_WORKERS", "4"))

# UvicornWorker wraps the FastAPI ASGI app in a uvicorn event loop so each
# gunicorn worker is a full async process — not a threaded sync worker.
worker_class = "uvicorn.workers.UvicornWorker"

# ── Timeouts ─────────────────────────────────────────────────────────────────
# Request timeout: abort workers that hang for > 120 seconds.
# Healthcare workloads (PDF generation, RIPS exports) can be slow but should
# never exceed this limit.  Long-running tasks should use RabbitMQ workers.
timeout = 120

# Keep-alive: how long to wait for the next request on a persistent connection.
keepalive = 5

# Graceful shutdown: allow up to 30 seconds for in-flight requests to finish
# before the worker is forcibly killed during a rolling restart.
graceful_timeout = 30

# ── Logging ───────────────────────────────────────────────────────────────────
# Write access and error logs to stdout/stderr so Docker captures them.
# These are aggregated by the container runtime (journald / Loki / CloudWatch).
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()

# ── Worker recycling ─────────────────────────────────────────────────────────
# Restart each worker after handling N requests to prevent slow memory leaks.
# Jitter (±50) avoids all workers restarting simultaneously under load.
max_requests = 1000
max_requests_jitter = 50
