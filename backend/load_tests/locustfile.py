"""DentalOS load test — main Locust entry point.

Imports all user classes, initializes the token pool, and defines
the connection pool stress test shape.

Usage:
    # Full 500-user test (headless)
    locust -f load_tests/locustfile.py --headless -u 500 -r 25 -t 30m

    # Web UI mode
    locust -f load_tests/locustfile.py

    # Connection pool stress test
    locust -f load_tests/locustfile.py --tags pool_stress --headless

    # Conflict booking test
    locust -f load_tests/locustfile.py ConflictBookingUser --headless -u 100 -r 100
"""

import logging
import time

from locust import LoadTestShape, events, tag, task, constant

from load_tests.config import (
    DEFAULT_RUN_TIME,
    DEFAULT_SPAWN_RATE,
    DEFAULT_USERS,
    POOL_STRESS_STAGES,
    THRESHOLDS,
)
from load_tests.utils.token_pool import token_pool

# Import all user classes so Locust discovers them
from load_tests.scenarios.auth_scenario import AuthUser  # noqa: F401
from load_tests.scenarios.patient_scenario import ClinicalStaffUser  # noqa: F401
from load_tests.scenarios.odontogram_scenario import DoctorUser  # noqa: F401
from load_tests.scenarios.appointment_scenario import (  # noqa: F401
    ConflictBookingUser,
    NormalAppointmentUser,
)
from load_tests.scenarios.billing_scenario import OwnerUser  # noqa: F401
from load_tests.scenarios.health_scenario import MonitorUser  # noqa: F401
from load_tests.scenarios._base import DentalOSUser

logger = logging.getLogger("dentalos.loadtest")


# ─── Token Pool Initialization ──────────────────────────


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Load token pool from seed manifest before any VUs spawn."""
    if not token_pool.is_loaded:
        logger.info("Loading token pool from seed manifest...")
        try:
            token_pool.load()
            logger.info("Token pool loaded successfully")
        except FileNotFoundError:
            logger.error(
                "Seed manifest not found — run `make load-seed` first"
            )
            environment.runner.quit()
            return


# ─── Threshold Validation on Test Stop ──────────────────


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log p95 threshold violations at end of test."""
    stats = environment.stats
    violations = []

    for name, threshold_ms in THRESHOLDS.items():
        entry = stats.get(name, "GET") or stats.get(name, "POST")
        if entry and entry.num_requests > 0:
            p95 = entry.get_response_time_percentile(0.95) or 0
            if p95 > threshold_ms:
                violations.append(
                    f"  FAIL: {name} p95={p95:.0f}ms > threshold={threshold_ms}ms"
                )
            else:
                logger.info(
                    "PASS: %s p95=%.0fms <= %dms", name, p95, threshold_ms
                )

    if violations:
        logger.warning("Threshold violations:\n%s", "\n".join(violations))
    else:
        logger.info("All endpoints within p95 thresholds")

    # Log overall failure rate
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    if total_requests > 0:
        failure_rate = (total_failures / total_requests) * 100
        if failure_rate > 1.0:
            logger.warning(
                "Overall failure rate %.2f%% exceeds 1%% threshold", failure_rate
            )
        else:
            logger.info("Overall failure rate: %.2f%%", failure_rate)


# ─── Connection Pool Stress Test Shape ──────────────────


class PoolStressShape(LoadTestShape):
    """Custom load shape for DB connection pool stress testing.

    Ramp stages: 10 → 25 → 35 → 50 → 10 users (60s each).
    At 50 VUs with wait_time=0, pool_timeout (30s) should trigger 503s.
    Tests that the app returns 503 (pool timeout), NOT 500 (unhandled).

    Usage:
        locust -f load_tests/locustfile.py PoolStressUser --tags pool_stress
    """

    use_common_options = False

    def __init__(self) -> None:
        super().__init__()
        self.stages = POOL_STRESS_STAGES

    def tick(self) -> tuple[int, float] | None:
        elapsed = self.get_run_time()
        cumulative = 0

        for duration, users, spawn_rate in self.stages:
            cumulative += duration
            if elapsed < cumulative:
                return (users, spawn_rate)

        return None  # Test complete


class PoolStressUser(DentalOSUser):
    """VU that hammers the DB with zero wait time (pool stress test)."""

    wait_time = constant(0)
    fixed_count = 0  # Controlled by PoolStressShape

    def on_start(self) -> None:
        self.creds = token_pool.get_staff()
        self._setup_headers(self.creds)

    @tag("pool_stress")
    @task
    def hammer_patients(self) -> None:
        """GET /patients/ with no delay — max DB connection pressure."""
        import random

        from load_tests.utils.data_pool import random_patient_id

        if not self.creds.patient_ids:
            return

        pid = random_patient_id(self.creds.patient_ids)
        with self.client.get(
            f"{self.api}/patients/{pid}",
            name="GET /patients/{id} (pool_stress)",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 503:
                response.success()  # Expected: pool timeout
            elif response.status_code == 500:
                response.failure("500 instead of 503 — pool timeout not handled")
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Unexpected: {response.status_code}")
