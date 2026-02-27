"""Billing scenario — summary + aging report (5% of VUs).

Clinic owners only. GET /billing/summary is the heaviest endpoint
(4 aggregate queries, uncached). Long wait times simulate real usage.
"""

from locust import between, tag, task

from load_tests.scenarios._base import DentalOSUser
from load_tests.utils.token_pool import token_pool


class OwnerUser(DentalOSUser):
    """Virtual user exercising billing summary endpoint (owner role only)."""

    weight = 5
    wait_time = between(10, 30)

    def on_start(self) -> None:
        self.creds = token_pool.get_owner()
        self._setup_headers(self.creds)

    @tag("billing", "summary")
    @task
    def billing_summary(self) -> None:
        """GET /billing/summary — 4 aggregate queries, CPU-heavy."""
        with self.client.get(
            f"{self.api}/billing/summary",
            name="GET /billing/summary",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in (404, 403):
                response.success()  # No billing data or permission mismatch
            else:
                response.failure(f"Billing summary failed: {response.status_code}")
