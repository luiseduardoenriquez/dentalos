"""Mercado Pago payment gateway stub — INT-07.

This is a placeholder integration for future implementation.
Currently raises NotImplementedError on all operations.
The validate_config() method can be used to check if credentials are set.
"""

import logging

from app.core.config import settings

logger = logging.getLogger("dentalos.integrations.payments.mercadopago")


class MercadoPagoService:
    """Mercado Pago payment gateway stub."""

    def validate_config(self) -> bool:
        """Check if Mercado Pago credentials are configured."""
        return bool(settings.mercadopago_access_token)

    async def create_preference(
        self,
        *,
        tenant_id: str,
        invoice_id: str,
        amount_cents: int,
        description: str,
        payer_email: str,
    ) -> dict:
        """Create a payment preference (checkout link).

        Raises:
            NotImplementedError: Always — stub for future implementation.
        """
        raise NotImplementedError(
            "Mercado Pago integration pending (INT-07). "
            "Configure mercadopago_access_token and implement payment flow."
        )

    async def process_webhook(self, payload: dict) -> dict:
        """Process Mercado Pago IPN webhook.

        Raises:
            NotImplementedError: Always — stub for future implementation.
        """
        raise NotImplementedError(
            "Mercado Pago webhook processing pending (INT-07)."
        )


# Module-level singleton
mercadopago_service = MercadoPagoService()
