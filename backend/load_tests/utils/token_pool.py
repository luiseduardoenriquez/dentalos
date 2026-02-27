"""Pre-minted JWT token distribution across virtual users.

Reads seed_manifest.json and distributes (token, tenant_id, patient_ids, doctor_ids)
round-robin across Locust workers/users.
"""

import json
import logging
import threading
from dataclasses import dataclass, field

from load_tests.config import MANIFEST_PATH

logger = logging.getLogger("dentalos.loadtest.token_pool")


@dataclass
class TenantCredentials:
    """Credentials and data for a single tenant."""

    tenant_id: str
    schema_name: str
    patient_ids: list[str]
    doctor_ids: list[str]
    users: list[dict]  # Each: {user_id, email, role, token}


@dataclass
class UserCredentials:
    """Credentials assigned to a single virtual user."""

    user_id: str
    email: str
    password: str
    role: str
    token: str
    tenant_id: str
    schema_name: str
    patient_ids: list[str]
    doctor_ids: list[str]


class TokenPool:
    """Thread-safe round-robin distributor of pre-minted credentials."""

    def __init__(self) -> None:
        self._tenants: list[TenantCredentials] = []
        self._all_users: list[UserCredentials] = []
        self._counter = 0
        self._lock = threading.Lock()
        self._loaded = False
        # Separate lists by role for weighted scenarios
        self._doctors: list[UserCredentials] = []
        self._owners: list[UserCredentials] = []
        self._receptionists: list[UserCredentials] = []
        self._all_staff: list[UserCredentials] = []

    def load(self, path: str | None = None) -> None:
        """Load credentials from the seed manifest JSON file."""
        manifest_path = path or MANIFEST_PATH
        with open(manifest_path) as f:
            manifest = json.load(f)

        password = manifest["password"]

        for tenant_data in manifest["tenants"]:
            tenant_creds = TenantCredentials(
                tenant_id=tenant_data["tenant_id"],
                schema_name=tenant_data["schema_name"],
                patient_ids=tenant_data["patient_ids"],
                doctor_ids=tenant_data["doctor_ids"],
                users=tenant_data["users"],
            )
            self._tenants.append(tenant_creds)

            for user in tenant_data["users"]:
                uc = UserCredentials(
                    user_id=user["user_id"],
                    email=user["email"],
                    password=password,
                    role=user["role"],
                    token=user["token"],
                    tenant_id=tenant_data["tenant_id"],
                    schema_name=tenant_data["schema_name"],
                    patient_ids=tenant_data["patient_ids"],
                    doctor_ids=tenant_data["doctor_ids"],
                )
                self._all_users.append(uc)
                self._all_staff.append(uc)

                if user["role"] == "doctor":
                    self._doctors.append(uc)
                elif user["role"] == "clinic_owner":
                    self._owners.append(uc)
                elif user["role"] == "receptionist":
                    self._receptionists.append(uc)

        self._loaded = True
        logger.info(
            "TokenPool loaded: %d tenants, %d users (%d doctors, %d owners)",
            len(self._tenants),
            len(self._all_users),
            len(self._doctors),
            len(self._owners),
        )

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def _round_robin(self, pool: list[UserCredentials]) -> UserCredentials:
        """Get next credentials from a pool in round-robin fashion."""
        if not pool:
            raise RuntimeError("TokenPool is empty — run `make load-seed` first")
        with self._lock:
            idx = self._counter % len(pool)
            self._counter += 1
        return pool[idx]

    def get_staff(self) -> UserCredentials:
        """Get next staff credentials (any role) — for patient scenario."""
        return self._round_robin(self._all_staff)

    def get_doctor(self) -> UserCredentials:
        """Get next doctor credentials — for odontogram scenario."""
        return self._round_robin(self._doctors)

    def get_owner(self) -> UserCredentials:
        """Get next clinic_owner credentials — for billing scenario."""
        return self._round_robin(self._owners)

    def get_any(self) -> UserCredentials:
        """Get next credentials from any user — for auth scenario."""
        return self._round_robin(self._all_users)

    @property
    def tenants(self) -> list[TenantCredentials]:
        return self._tenants


# Module-level singleton
token_pool = TokenPool()
