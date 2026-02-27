"""Load test configuration — thresholds, constants, base URL."""

import os

# ─── Base URL ───────────────────────────────────────────
BASE_URL = os.getenv("LOAD_TEST_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"

# ─── Virtual User Distribution (500 total) ──────────────
VU_WEIGHTS = {
    "auth": 10,          # 50 VUs
    "patient": 40,       # 200 VUs
    "odontogram": 25,    # 125 VUs
    "appointment": 15,   # 75 VUs
    "billing": 5,        # 25 VUs
    # health: fixed 5 VUs (not weighted)
}
HEALTH_FIXED_COUNT = 5

# ─── Test Duration ──────────────────────────────────────
DEFAULT_USERS = 500
DEFAULT_SPAWN_RATE = 25    # Users per second during ramp-up
DEFAULT_RUN_TIME = "30m"

# ─── P95 Latency Thresholds (milliseconds) ─────────────
THRESHOLDS = {
    "GET /patients/search":      150,   # Redis cached 120s
    "GET /patients/":            200,   # Paginated, no cache
    "GET /patients/{id}":        200,   # Single record
    "POST /patients":            300,   # Insert + validation
    "PUT /patients/{id}":        300,   # Update
    "GET /odontogram/{id}":      100,   # Redis cached 5min
    "POST /odontogram/bulk":     500,   # Heavy write + cache invalidation
    "POST /odontogram":          300,   # Single condition
    "POST /appointments":        500,   # Overlap check + insert
    "GET /billing/summary":      1000,  # 4 aggregate queries, uncached
    "POST /auth/login":          800,   # bcrypt cost=12, CPU-bound
    "POST /auth/refresh-token":  100,   # Fast path
    "GET /health":               300,   # Checks all deps
}

# ─── Seed Constants ─────────────────────────────────────
NUM_TENANTS = 10
PATIENTS_PER_TENANT = 250
DOCTORS_PER_TENANT = 3
USERS_PER_TENANT = 5  # 1 owner + 3 doctors + 1 receptionist
LOAD_PASSWORD = "LoadTest2026!"
TOKEN_TTL_HOURS = 2

# ─── Seed Manifest Path ────────────────────────────────
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "seed_manifest.json")

# ─── Connection Pool Stress ─────────────────────────────
POOL_STRESS_STAGES = [
    # (duration_seconds, target_users, spawn_rate)
    (60, 10, 10),
    (60, 25, 5),
    (60, 35, 5),
    (60, 50, 5),
    (60, 10, 10),  # Step-down — recovery
]

# ─── RabbitMQ Monitoring ────────────────────────────────
RABBITMQ_API_URL = os.getenv(
    "RABBITMQ_API_URL", "http://localhost:15672/api"
)
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "dentalos")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "dentalos_dev_password")
RABBITMQ_VHOST = "%2Fdentalos"  # URL-encoded /dentalos
QUEUE_DEPTH_THRESHOLD = 500

# ─── Common Colombian Name Prefixes for Search ─────────
SEARCH_PREFIXES = [
    "Ma", "Ca", "An", "Lu", "Jo", "Da", "Sa", "Va", "Is", "Mi",
    "Pa", "Fe", "Se", "Di", "Na", "So", "Ga", "Al", "Ju", "Cr",
    "Ra", "La", "He", "Ro", "To", "Mo", "Me", "Pe", "Go", "Vi",
]

# ─── Conflict Test ──────────────────────────────────────
CONFLICT_VUS = 100
