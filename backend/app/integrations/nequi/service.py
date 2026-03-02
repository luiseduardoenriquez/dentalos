"""Nequi QR Push payment service -- production implementation.

Integrates with the Nequi Payments API v2 (QR Push model) to generate
QR codes for in-clinic payment collection and query payment status.

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
from app.integrations.nequi.base import NequiServiceBase
from app.integrations.nequi.schemas import NequiPaymentStatus, NequiQRResponse

logger = logging.getLogger("dentalos.integrations.nequi")

# Nequi QR Push API path patterns
_QR_GENERATE_PATH = "/payments/v2/-services-paymentservice-qr-generate"
_PAYMENT_STATUS_PATH = "/payments/v2/-services-paymentservice-status"
_OAUTH_TOKEN_PATH = "/oauth/token"


class NequiService(NequiServiceBase):
    """Production Nequi QR payment service using Nequi Payments API v2."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    def is_configured(self) -> bool:
        """Check if all required Nequi credentials are set."""
        return bool(
            settings.nequi_client_id
            and settings.nequi_client_secret
            and settings.nequi_api_key
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a lazily-initialized async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.nequi_base_url,
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def _get_access_token(self) -> str:
        """Obtain or return a cached OAuth2 client_credentials access token.

        The token is requested from Nequi's OAuth endpoint and cached in
        memory until 60 seconds before its stated expiry time. Tokens are
        never logged or persisted to disk.

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
                "client_id": settings.nequi_client_id,
                "client_secret": settings.nequi_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()

        token_data: dict[str, Any] = response.json()
        self._access_token = token_data["access_token"]
        expires_in = int(token_data.get("expires_in", 3600))
        self._token_expires_at = now + expires_in

        logger.info("Nequi OAuth token acquired, expires_in=%d", expires_in)
        return self._access_token

    async def _auth_headers(self) -> dict[str, str]:
        """Build authorization headers for API requests."""
        token = await self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "x-api-key": settings.nequi_api_key,
            "Content-Type": "application/json",
        }

    async def generate_qr_payment(
        self,
        *,
        amount_cents: int,
        reference: str,
        description: str,
    ) -> NequiQRResponse:
        """Generate a Nequi QR code for push payment.

        Calls the Nequi QR Push API to create a scannable QR code that
        patients can pay from their Nequi app.

        Args:
            amount_cents: Payment amount in COP cents.
            reference: Unique DentalOS payment reference.
            description: Human-readable description (no PHI).

        Returns:
            NequiQRResponse with QR URL, payment ID, and expiry.

        Raises:
            httpx.HTTPStatusError: On Nequi API failure.
        """
        if not self.is_configured():
            raise RuntimeError("Nequi integration is not configured")

        client = await self._get_client()
        headers = await self._auth_headers()

        # Nequi expects amount in COP (not cents) as a string
        amount_cop = str(amount_cents // 100)

        payload = {
            "RequestMessage": {
                "RequestHeader": {
                    "Channel": "PQR03",
                    "RequestDate": "",
                    "MessageID": reference,
                    "ClientID": settings.nequi_client_id,
                },
                "RequestBody": {
                    "any": {
                        "generateCodeQRRQ": {
                            "code": reference,
                            "value": amount_cop,
                        }
                    }
                },
            }
        }

        response = await client.post(
            _QR_GENERATE_PATH,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        # Extract from Nequi response envelope
        body = (
            data.get("ResponseMessage", {})
            .get("ResponseBody", {})
            .get("any", {})
            .get("generateCodeQRRS", {})
        )

        result = NequiQRResponse(
            qr_code_url=body.get("qrCodeUrl", ""),
            payment_id=body.get("transactionId", ""),
            status="pending",
            expires_at=body.get("expiresAt", ""),
        )

        # Log only truncated payment_id for traceability (no amounts)
        logger.info(
            "Nequi QR generated: payment_id=%s...",
            result.payment_id[:8] if result.payment_id else "unknown",
        )

        return result

    async def get_payment_status(
        self,
        *,
        payment_id: str,
    ) -> NequiPaymentStatus:
        """Query current status of a Nequi payment.

        Args:
            payment_id: Nequi-assigned payment identifier.

        Returns:
            NequiPaymentStatus with current state.

        Raises:
            httpx.HTTPStatusError: On Nequi API failure.
        """
        if not self.is_configured():
            raise RuntimeError("Nequi integration is not configured")

        client = await self._get_client()
        headers = await self._auth_headers()

        response = await client.get(
            f"{_PAYMENT_STATUS_PATH}/{payment_id}",
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        body = (
            data.get("ResponseMessage", {})
            .get("ResponseBody", {})
            .get("any", {})
            .get("getStatusPaymentRS", {})
        )

        result = NequiPaymentStatus(
            payment_id=payment_id,
            status=body.get("status", "pending"),
            amount_cents=int(body.get("value", "0")) * 100,
            reference=body.get("code", ""),
            completed_at=body.get("completedAt"),
        )

        logger.info(
            "Nequi payment status queried: payment_id=%s... status=%s",
            payment_id[:8],
            result.status,
        )

        return result

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 webhook signature from Nequi.

        Uses timing-safe comparison to prevent timing attacks.

        Args:
            payload: Raw HTTP request body bytes.
            signature: Value of the X-Nequi-Signature header.

        Returns:
            True if the signature is valid.
        """
        if not settings.nequi_webhook_secret:
            logger.warning("Nequi webhook secret not configured")
            return False

        secret = settings.nequi_webhook_secret.encode("utf-8")
        computed = hmac.new(secret, payload, hashlib.sha256).hexdigest()

        return hmac.compare_digest(computed, signature)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Module-level singleton
nequi_service = NequiService()
