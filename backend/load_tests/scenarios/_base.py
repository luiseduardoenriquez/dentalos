"""Base user class for all DentalOS load test scenarios."""

import random

from locust import HttpUser

from load_tests.config import API_PREFIX, BASE_URL
from load_tests.utils.token_pool import UserCredentials


class DentalOSUser(HttpUser):
    """Base class providing auth headers and API prefix."""

    abstract = True
    host = BASE_URL

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.api = API_PREFIX
        # Each VU gets a unique X-Forwarded-For to avoid per-IP rate limits
        self._spoofed_ip = f"10.0.{random.randint(0, 255)}.{random.randint(1, 254)}"

    def _setup_headers(self, creds: UserCredentials) -> None:
        """Set authentication and IP headers for this VU."""
        self.client.headers.update({
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
            "X-Forwarded-For": self._spoofed_ip,
        })
