"""Patient scenario — search + list + CRUD (40% of VUs).

50% search, 25% list, 15% detail, 5% create, 5% update.
Exercises Redis-cached search and paginated list endpoints.
"""

from locust import between, tag, task

from load_tests.scenarios._base import DentalOSUser
from load_tests.utils.data_pool import (
    random_patient_id,
    random_patient_payload,
    random_search_prefix,
)
from load_tests.utils.token_pool import token_pool


class ClinicalStaffUser(DentalOSUser):
    """Virtual user exercising patient CRUD endpoints."""

    weight = 40
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.creds = token_pool.get_staff()
        self._setup_headers(self.creds)

    @tag("patients", "search")
    @task(50)
    def search_patients(self) -> None:
        """GET /patients/search?q={prefix} — Redis cached."""
        prefix = random_search_prefix()
        with self.client.get(
            f"{self.api}/patients/search",
            params={"q": prefix},
            name="GET /patients/search",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")

    @tag("patients", "list")
    @task(25)
    def list_patients(self) -> None:
        """GET /patients/ — paginated list."""
        import random

        page = random.randint(1, 10)
        with self.client.get(
            f"{self.api}/patients/",
            params={"page": page, "page_size": 20},
            name="GET /patients/",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List failed: {response.status_code}")

    @tag("patients", "detail")
    @task(15)
    def get_patient_detail(self) -> None:
        """GET /patients/{id} — single patient record."""
        if not self.creds.patient_ids:
            return
        pid = random_patient_id(self.creds.patient_ids)
        with self.client.get(
            f"{self.api}/patients/{pid}",
            name="GET /patients/{id}",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Detail failed: {response.status_code}")

    @tag("patients", "create")
    @task(5)
    def create_patient(self) -> None:
        """POST /patients — create new patient."""
        payload = random_patient_payload()
        with self.client.post(
            f"{self.api}/patients",
            json=payload,
            name="POST /patients",
            catch_response=True,
        ) as response:
            if response.status_code in (201, 409):  # 409 = duplicate document
                response.success()
            else:
                response.failure(f"Create failed: {response.status_code}")

    @tag("patients", "update")
    @task(5)
    def update_patient(self) -> None:
        """PUT /patients/{id} — update existing patient."""
        if not self.creds.patient_ids:
            return
        pid = random_patient_id(self.creds.patient_ids)
        with self.client.put(
            f"{self.api}/patients/{pid}",
            json={"phone": f"+573{__import__('random').randint(100000000, 999999999)}"},
            name="PUT /patients/{id}",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Update failed: {response.status_code}")
