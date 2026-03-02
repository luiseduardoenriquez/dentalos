"""Daviplata QR payment service -- production implementation.

Integrates with the Daviplata Payments API to generate QR codes for
in-clinic payment collection and query payment status.

Security:
  - OAuth2 client_credentials tokens stored only in memory, never logged
  - All httpx calls use explicit 30s timeouts
  - Webhook signatures verified with timing-safe HMAC-SHA256
  - Payment amounts and references are NEVER logged in full
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.daviplata.base import DaviplataServiceBase
from app.integrations.daviplata.schemas import (
    DaviplataPaymentStatus,
    DaviplataQRResponse,
)

logger = logging.getLogger("dentalos.integrations.daviplata")

# Daviplata API path patterns
_QR_GENERATE_PATH = "/payments/qr/generate"
_PAYMENT_STATUS_PATH = "/payments/status"
_OAUTH_TOKEN_PATH = "/oauth2/token"


class DaviplataService(DaviplataServiceBase):
    """Production Daviplata QR payment service."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    def is_configured(self) -> bool:
        """Check if all required Daviplata credentials are set."""
        return bool(
            settings.daviplata_client_id
            and settings.daviplata_client_secret
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a lazily-initialized async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.daviplata_base_url,
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def _get_access_token(self) -> str:
        """Obtain or return a cached OAuth2 client_credentials access token.

        The token is requested from Daviplata's OAuth2 endpoint and cached
        in memory until 60 seconds before its stated expiry time. Tokens
        are never logged or persisted to disk.

        Returns:
            A valid access token string.

        Raises:
            httpx.HTTPStatusError: If the token request fails.
        """
        now = time.monotonic()

        # Return cached token if still valid (with 60s safety margin)
        if self._access_token and now < (self._token_expires_at - 60):
            return self._access_token

        client = await self._get_client()
        response = await client.post(
            _OAUTH_TOKEN_PATH,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.daviplata_client_id,
                "client_secret": settings.daviplata_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()

        token_data: dict[str, Any] = response.json()
        self._access_token = token_data["access_token"]
        expires_in = int(token_data.get("expires_in", 3600))
        self._token_expires_at = now + expires_in

        logger.info("Daviplata OAuth token acquired, expires_in=%d", expires_in)
        return self._access_token

    async def _auth_headers(self) -> dict[str, str]:
        """Build authorization headers for API requests."""
        token = await self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def generate_qr_payment(
        self,
        *,
        amount_cents: int,
        reference: str,
        description: str,
    ) -> DaviplataQRResponse:
        """Generate a Daviplata QR code for payment.

        Calls the Daviplata QR API to create a scannable QR code that
        patients can pay from their Daviplata app.

        Args:
            amount_cents: Payment amount in COP cents.
            reference: Unique DentalOS payment reference.
            description: Human-readable description (no PHI).

        Returns:
            DaviplataQRResponse with QR URL, payment ID, and expiry.

        Raises:
            httpx.HTTPStatusError: On Daviplata API failure.
        """
        if not self.is_configured():
            raise RuntimeError("Daviplata integration is not configured")

        client = await self._get_client()
        headers = await self._auth_headers()

        # Daviplata expects amount in COP (not cents) as an integer
        amount_cop = amount_cents // 100

        payload = {
            "amount": amount_cop,
            "reference": reference,
            "description": description,
            "currency": "COP",
        }

        response = await client.post(
            _QR_GENERATE_PATH,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        result = DaviplataQRResponse(
            qr_code_url=data.get("qr_code_url", ""),
            payment_id=data.get("payment_id", ""),
            status="pending",
            expires_at=data.get("expires_at", ""),
        )

        # Log only truncated payment_id for traceability (no amounts)
        logger.info(
            "Daviplata QR generated: payment_id=%s...",
            result.payment_id[:8] if result.payment_id else "unknown",
        )

        return result

    async def get_payment_status(
        self,
        *,
        payment_id: str,
    ) -> DaviplataPaymentStatus:
        """Query current status of a Daviplata payment.

        Args:
            payment_id: Daviplata-assigned payment identifier.

        Returns:
            DaviplataPaymentStatus with current state.

        Raises:
            httpx.HTTPStatusError: On Daviplata API failure.
        """
        if not self.is_configured():
            raise RuntimeError("Daviplata integration is not configured")

        client = await self._get_client()
        headers = await self._auth_headers()

        response = await client.get(
            f"{_PAYMENT_STATUS_PATH}/{payment_id}",
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        result = DaviplataPaymentStatus(
            payment_id=payment_id,
            status=data.get("status", "pending"),
            amount_cents=int(data.get("amount", 0)) * 100,
            reference=data.get("reference", ""),
            completed_at=data.get("completed_at"),
        )

        logger.info(
            "Daviplata payment status queried: payment_id=%s... status=%s",
            payment_id[:8],
            result.status,
        )

        return result

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 webhook signature from Daviplata.

        Uses timing-safe comparison to prevent timing attacks.

        Args:
            payload: Raw HTTP request body bytes.
            signature: Value of the X-Daviplata-Signature header.

        Returns:
            True if the signature is valid.
        """
        if not settings.daviplata_webhook_secret:
            logger.warning("Daviplata webhook secret not configured")
            return False

        secret = settings.daviplata_webhook_secret.encode("utf-8")
        computed = hmac.new(secret, payload, hashlib.sha256).hexdigest()

        return hmac.compare_digest(computed, signature)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Module-level singleton
daviplata_service = DaviplataService()
