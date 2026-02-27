"""Appointment scenario — create + conflict test (15% of VUs).

Normal mode: books appointments across future slots, spread across doctors.
Conflict mode: 100 VUs all target same doctor+timeslot (expects 1x 201, rest 409).
"""

import threading

from locust import between, constant, tag, task

from load_tests.scenarios._base import DentalOSUser
from load_tests.utils.data_pool import (
    random_appointment_payload,
    random_doctor_id,
    random_future_date,
    random_patient_id,
    random_time_slot,
)
from load_tests.utils.token_pool import token_pool


class NormalAppointmentUser(DentalOSUser):
    """Virtual user that books appointments normally (spread across doctors/slots)."""

    weight = 15
    wait_time = between(2, 5)

    def on_start(self) -> None:
        self.creds = token_pool.get_staff()
        self._setup_headers(self.creds)

    @tag("appointments", "create")
    @task
    def book_appointment(self) -> None:
        """POST /appointments — normal booking across various slots."""
        if not self.creds.patient_ids or not self.creds.doctor_ids:
            return
        payload = random_appointment_payload(
            doctor_id=random_doctor_id(self.creds.doctor_ids),
            patient_id=random_patient_id(self.creds.patient_ids),
        )
        with self.client.post(
            f"{self.api}/appointments",
            json=payload,
            name="POST /appointments",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201, 409):
                response.success()
            elif response.status_code == 422:
                response.success()  # Validation errors from random data
            else:
                response.failure(f"Booking failed: {response.status_code}")


# ─── Conflict Booking Test ──────────────────────────────

# Shared state for conflict test synchronization
_conflict_barrier: threading.Barrier | None = None
_conflict_slot: dict | None = None
_conflict_results: dict = {"created": 0, "conflict": 0, "error": 0}
_conflict_lock = threading.Lock()


def setup_conflict_test(num_vus: int, doctor_id: str, patient_ids: list[str]) -> None:
    """Initialize shared state for the conflict test. Called from locustfile."""
    global _conflict_barrier, _conflict_slot
    _conflict_barrier = threading.Barrier(num_vus, timeout=30)
    _conflict_slot = {
        "doctor_id": doctor_id,
        "date": random_future_date(days_ahead_min=1, days_ahead_max=1),
        "start_time": "09:00",
        "duration_minutes": 30,
        "type": "consultation",
        "notes": "Conflict load test",
    }


class ConflictBookingUser(DentalOSUser):
    """100 VUs all target the same doctor+timeslot simultaneously.

    Expected: exactly 1x 201 + 99x 409. Any 500 = test failure.
    """

    wait_time = constant(0)
    fixed_count = 0  # Not used in weighted mode — only in conflict test

    def on_start(self) -> None:
        self.creds = token_pool.get_staff()
        self._setup_headers(self.creds)

    @tag("appointments", "conflict")
    @task
    def conflict_booking(self) -> None:
        """All VUs attempt to book the same slot simultaneously."""
        global _conflict_results

        if not _conflict_slot or not self.creds.patient_ids:
            return

        # Wait for all VUs to be ready
        if _conflict_barrier:
            try:
                _conflict_barrier.wait()
            except threading.BrokenBarrierError:
                return

        payload = {
            **_conflict_slot,
            "patient_id": random_patient_id(self.creds.patient_ids),
        }

        with self.client.post(
            f"{self.api}/appointments",
            json=payload,
            name="POST /appointments (conflict)",
            catch_response=True,
        ) as response:
            with _conflict_lock:
                if response.status_code == 201:
                    _conflict_results["created"] += 1
                    response.success()
                elif response.status_code == 409:
                    _conflict_results["conflict"] += 1
                    response.success()
                elif response.status_code == 422:
                    _conflict_results["conflict"] += 1
                    response.success()  # Overlap rejection via validation
                elif response.status_code == 500:
                    _conflict_results["error"] += 1
                    response.failure("500 error in conflict test — unhandled race condition")
                else:
                    response.failure(f"Unexpected status: {response.status_code}")

        # Stop after one attempt — conflict test is a single-shot
        self.environment.runner.quit()


def get_conflict_results() -> dict:
    """Return conflict test result counts."""
    return dict(_conflict_results)
