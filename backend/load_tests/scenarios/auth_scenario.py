"""Auth scenario — login + refresh-token (10% of VUs).

80% refresh-token (fast path), 20% full login (bcrypt, CPU-bound).
Uses real credentials from the seed manifest.
"""

import random

from locust import between, tag, task

from load_tests.scenarios._base import DentalOSUser
from load_tests.utils.token_pool import token_pool


class AuthUser(DentalOSUser):
    """Virtual user that exercises authentication endpoints."""

    weight = 10
    wait_time = between(2, 5)

    def on_start(self) -> None:
        self.creds = token_pool.get_any()
        self._setup_headers(self.creds)
        self._refresh_token: str | None = None

    @tag("auth", "refresh")
    @task(80)
    def refresh_token(self) -> None:
        """POST /auth/refresh-token — fast path."""
        # If we don't have a refresh token yet, do a login first
        if not self._refresh_token:
            self._do_login()
            return

        with self.client.post(
            f"{self.api}/auth/refresh-token",
            json={"refresh_token": self._refresh_token},
            name="POST /auth/refresh-token",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self._refresh_token = data.get("refresh_token", self._refresh_token)
                # Update access token
                new_token = data.get("access_token")
                if new_token:
                    self.client.headers["Authorization"] = f"Bearer {new_token}"
                response.success()
            elif response.status_code == 401:
                # Token expired — re-login
                self._refresh_token = None
                response.success()  # Expected behavior
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @tag("auth", "login")
    @task(20)
    def login(self) -> None:
        """POST /auth/login — full bcrypt verification."""
        self._do_login()

    def _do_login(self) -> None:
        """Perform a full login and store the refresh token."""
        with self.client.post(
            f"{self.api}/auth/login",
            json={
                "email": self.creds.email,
                "password": self.creds.password,
                "tenant_id": self.creds.tenant_id,
            },
            name="POST /auth/login",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self._refresh_token = data.get("refresh_token")
                new_token = data.get("access_token")
                if new_token:
                    self.client.headers["Authorization"] = f"Bearer {new_token}"
                response.success()
            elif response.status_code == 429:
                # Rate limited — expected under load
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")
