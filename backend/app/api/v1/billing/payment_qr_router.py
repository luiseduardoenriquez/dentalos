"""QR payment generation endpoint for Nequi/Daviplata.

POST /billing/invoices/{invoice_id}/payment-qr -- Generate a QR code for payment.

Sprint 23-24 / VP-05: Nequi/Daviplata QR Payments.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.payment_qr import PaymentQRRequest, PaymentQRResponse
from app.services.payment_qr_service import payment_qr_service

logger = logging.getLogger("dentalos.billing.payment_qr")

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post(
    "/invoices/{invoice_id}/payment-qr",
    response_model=PaymentQRResponse,
    status_code=200,
)
async def generate_payment_qr(
    invoice_id: UUID,
    body: PaymentQRRequest,
    current_user: AuthenticatedUser = Depends(require_permission("billing:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Generate a QR code for paying an invoice via Nequi or Daviplata.

    Requires ``billing:write`` permission. Returns a base64-encoded PNG QR
    code image that can be displayed on screen for the patient to scan.

    The QR code is valid for 15 minutes. After expiry, a new one must be
    generated.
    """
    return await payment_qr_service.generate_payment_qr(
        db=db,
        invoice_id=invoice_id,
        provider=body.provider,
        tenant_id=current_user.tenant.tenant_id,
    )
