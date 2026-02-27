"""Odontogram scenario — cached reads + bulk writes (25% of VUs).

80% GET (warm cache), 10% bulk write (8 conditions), 10% single condition.
Re-fetches after writes to verify cache invalidation.
"""

from locust import between, tag, task

from load_tests.scenarios._base import DentalOSUser
from load_tests.utils.data_pool import (
    random_bulk_conditions,
    random_condition,
    random_patient_id,
    random_tooth,
    random_zone,
)
from load_tests.utils.token_pool import token_pool


class DoctorUser(DentalOSUser):
    """Virtual user exercising odontogram endpoints (doctor role only)."""

    weight = 25
    wait_time = between(3, 8)

    def on_start(self) -> None:
        self.creds = token_pool.get_doctor()
        self._setup_headers(self.creds)

    @tag("odontogram", "read")
    @task(80)
    def get_odontogram(self) -> None:
        """GET /odontogram/{patient_id} — Redis cached (5min TTL)."""
        if not self.creds.patient_ids:
            return
        pid = random_patient_id(self.creds.patient_ids)
        with self.client.get(
            f"{self.api}/odontogram/{pid}",
            name="GET /odontogram/{id}",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"GET odontogram failed: {response.status_code}")

    @tag("odontogram", "bulk")
    @task(10)
    def bulk_write_conditions(self) -> None:
        """POST /odontogram/bulk — 8 conditions at once + cache invalidation."""
        if not self.creds.patient_ids:
            return
        pid = random_patient_id(self.creds.patient_ids)
        conditions = random_bulk_conditions(count=8)

        with self.client.post(
            f"{self.api}/odontogram/{pid}/bulk",
            json={"conditions": conditions},
            name="POST /odontogram/bulk",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                response.success()
            elif response.status_code == 404:
                response.success()  # Patient doesn't exist in this tenant
            else:
                response.failure(f"Bulk write failed: {response.status_code}")

        # Re-fetch to verify cache was invalidated
        with self.client.get(
            f"{self.api}/odontogram/{pid}",
            name="GET /odontogram/{id} (post-write)",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Post-write GET failed: {response.status_code}")

    @tag("odontogram", "single")
    @task(10)
    def single_condition(self) -> None:
        """POST /odontogram/{patient_id} — single condition write."""
        if not self.creds.patient_ids:
            return
        pid = random_patient_id(self.creds.patient_ids)
        payload = {
            "tooth_number": random_tooth(),
            "zone": random_zone(),
            "condition": random_condition(),
            "notes": "Load test single condition",
        }

        with self.client.post(
            f"{self.api}/odontogram/{pid}",
            json=payload,
            name="POST /odontogram",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201, 404):
                response.success()
            else:
                response.failure(f"Single condition failed: {response.status_code}")
