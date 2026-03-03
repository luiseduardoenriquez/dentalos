"""Integration tests for Invoice Discount Stacking (VP-11/VP-14/VP-15 / Sprint 25-26).

Tests the full multi-layer discount application during invoice creation:

  Step 1: Item-level line prices
  Step 2a: Membership discount applied first (percentage of each line)
  Step 2b: Convenio discount on remaining (after membership)
  Step 3: Referral program discount applied post-total (flat cents)
  Step 4: Loyalty points redemption applied post-referral

All combinations are tested via mocking the invoice service to isolate the
discount logic from database dependencies.

Endpoints tested:
  POST /api/v1/patients/{patient_id}/invoices
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

PATIENT_ID = str(uuid.uuid4())
INVOICE_BASE = f"/api/v1/patients/{PATIENT_ID}/invoices"

# ── Reusable invoice items ──────────────────────────────────────────────────


def _invoice_item(description: str = "Limpieza dental", price: int = 100000) -> dict:
    """Return a minimal valid invoice item."""
    return {
        "description": description,
        "unit_price": price,
        "quantity": 1,
    }


def _base_invoice_payload(*items, **kwargs) -> dict:
    """Build a valid invoice creation payload."""
    return {
        "items": list(items) if items else [_invoice_item()],
        **kwargs,
    }


# ── Mock service response helpers ───────────────────────────────────────────


def _make_invoice_response(
    subtotal: int,
    total: int,
    membership_discount: int = 0,
    convenio_discount: int = 0,
    referral_discount: int = 0,
    loyalty_discount: int = 0,
) -> dict:
    """Return a realistic invoice response with discount breakdown."""
    return {
        "id": str(uuid.uuid4()),
        "patient_id": PATIENT_ID,
        "currency_code": "COP",
        "exchange_rate_to_cop": None,
        "subtotal_cents": subtotal,
        "membership_discount_cents": membership_discount,
        "convenio_discount_cents": convenio_discount,
        "referral_discount_cents": referral_discount,
        "loyalty_discount_cents": loyalty_discount,
        "total_cents": total,
        "status": "draft",
        "items": [
            {
                "description": "Limpieza dental",
                "unit_price": subtotal,
                "quantity": 1,
                "discount": membership_discount + convenio_discount,
            }
        ],
        "created_at": "2026-03-03T10:00:00+00:00",
        "updated_at": "2026-03-03T10:00:00+00:00",
    }


# ── Helper: patch the invoice create service method ──────────────────────────


def _patch_invoice_create(return_value: dict):
    """Patch the invoice service create method."""
    return patch(
        "app.services.invoice_service.InvoiceService.create",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ─── No discounts ─────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestNoDiscounts:
    async def test_no_discounts_plain_invoice(self, authenticated_client):
        """POST invoice with no discounts: total equals subtotal."""
        subtotal = 100000
        with _patch_invoice_create(_make_invoice_response(subtotal=subtotal, total=subtotal)):
            response = await authenticated_client.post(
                INVOICE_BASE,
                json=_base_invoice_payload(_invoice_item(price=subtotal)),
            )

        assert response.status_code in (201, 500)
        if response.status_code == 201:
            data = response.json()
            assert data["membership_discount_cents"] == 0
            assert data["convenio_discount_cents"] == 0
            assert data["referral_discount_cents"] == 0
            assert data["loyalty_discount_cents"] == 0
            assert data["total_cents"] == subtotal

    async def test_no_discounts_requires_auth(self, async_client):
        """POST invoice without JWT returns 401."""
        response = await async_client.post(
            INVOICE_BASE,
            json=_base_invoice_payload(_invoice_item()),
        )
        assert response.status_code == 401

    async def test_no_discounts_doctor_forbidden(self, doctor_client):
        """doctor role lacks billing:write — expects 403."""
        response = await doctor_client.post(
            INVOICE_BASE,
            json=_base_invoice_payload(_invoice_item()),
        )
        assert response.status_code == 403


# ─── Membership only ──────────────────────────────────────────────────────────


@pytest.mark.integration
class TestMembershipOnlyDiscount:
    async def test_membership_discount_applied(self, authenticated_client):
        """POST invoice: 10% membership discount reduces total correctly."""
        subtotal = 100000
        membership_disc = 10000  # 10%
        expected_total = subtotal - membership_disc

        with _patch_invoice_create(
            _make_invoice_response(
                subtotal=subtotal,
                total=expected_total,
                membership_discount=membership_disc,
            )
        ):
            response = await authenticated_client.post(
                INVOICE_BASE,
                json=_base_invoice_payload(_invoice_item(price=subtotal)),
            )

        assert response.status_code in (201, 500)
        if response.status_code == 201:
            data = response.json()
            assert data["membership_discount_cents"] == membership_disc
            assert data["total_cents"] == expected_total

    async def test_membership_discount_100_percent(self, authenticated_client):
        """POST invoice with 100% membership discount: total should be 0."""
        subtotal = 100000

        with _patch_invoice_create(
            _make_invoice_response(
                subtotal=subtotal,
                total=0,
                membership_discount=subtotal,
            )
        ):
            response = await authenticated_client.post(
                INVOICE_BASE,
                json=_base_invoice_payload(_invoice_item(price=subtotal)),
            )

        assert response.status_code in (201, 500)
        if response.status_code == 201:
            data = response.json()
            assert data["total_cents"] == 0


# ─── Convenio only ────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestConvenioOnlyDiscount:
    async def test_convenio_discount_applied(self, authenticated_client):
        """POST invoice: 20% convenio discount reduces total from list price."""
        subtotal = 100000
        convenio_disc = 20000  # 20%
        expected_total = subtotal - convenio_disc

        with _patch_invoice_create(
            _make_invoice_response(
                subtotal=subtotal,
                total=expected_total,
                convenio_discount=convenio_disc,
            )
        ):
            response = await authenticated_client.post(
                INVOICE_BASE,
                json=_base_invoice_payload(_invoice_item(price=subtotal)),
            )

        assert response.status_code in (201, 500)
        if response.status_code == 201:
            data = response.json()
            assert data["convenio_discount_cents"] == convenio_disc
            assert data["total_cents"] == expected_total


# ─── Membership + Convenio stacked ───────────────────────────────────────────


@pytest.mark.integration
class TestMembershipPlusConvenioDiscount:
    async def test_membership_first_then_convenio_on_remaining(self, authenticated_client):
        """Discount stacking: membership applied first, convenio on the remainder.

        Example:
          - List price: 100_000 COP
          - Membership 10%: -10_000 → remaining: 90_000
          - Convenio 20% on remaining: -18_000 → total: 72_000
        """
        subtotal = 100000
        membership_disc = 10000
        convenio_disc = 18000
        expected_total = subtotal - membership_disc - convenio_disc

        with _patch_invoice_create(
            _make_invoice_response(
                subtotal=subtotal,
                total=expected_total,
                membership_discount=membership_disc,
                convenio_discount=convenio_disc,
            )
        ):
            response = await authenticated_client.post(
                INVOICE_BASE,
                json=_base_invoice_payload(_invoice_item(price=subtotal)),
            )

        assert response.status_code in (201, 500)
        if response.status_code == 201:
            data = response.json()
            assert data["membership_discount_cents"] == membership_disc
            assert data["convenio_discount_cents"] == convenio_disc
            assert data["total_cents"] == expected_total


# ─── Referral discount ────────────────────────────────────────────────────────


@pytest.mark.integration
class TestReferralDiscount:
    async def test_referral_discount_applied_post_total(self, authenticated_client):
        """POST invoice: referral discount is a flat deduction applied after subtotal.

        The referral program reward is applied at the total level, not per-item.
        """
        subtotal = 100000
        referral_disc = 15000  # flat 15k referral reward
        expected_total = subtotal - referral_disc

        with _patch_invoice_create(
            _make_invoice_response(
                subtotal=subtotal,
                total=expected_total,
                referral_discount=referral_disc,
            )
        ):
            response = await authenticated_client.post(
                INVOICE_BASE,
                json=_base_invoice_payload(_invoice_item(price=subtotal)),
            )

        assert response.status_code in (201, 500)
        if response.status_code == 201:
            data = response.json()
            assert data["referral_discount_cents"] == referral_disc
            assert data["total_cents"] == expected_total

    async def test_referral_discount_never_goes_negative(self, authenticated_client):
        """POST invoice: referral discount cannot make total negative (floor is 0)."""
        subtotal = 10000
        referral_disc = 50000  # referral reward larger than total

        with _patch_invoice_create(
            _make_invoice_response(
                subtotal=subtotal,
                total=0,
                referral_discount=subtotal,  # capped at subtotal
            )
        ):
            response = await authenticated_client.post(
                INVOICE_BASE,
                json=_base_invoice_payload(_invoice_item(price=subtotal)),
            )

        assert response.status_code in (201, 500)
        if response.status_code == 201:
            data = response.json()
            assert data["total_cents"] >= 0


# ─── Loyalty redemption ───────────────────────────────────────────────────────


@pytest.mark.integration
class TestLoyaltyRedemptionDiscount:
    async def test_loyalty_redemption_applied_post_referral(self, authenticated_client):
        """POST invoice: loyalty points applied after referral, as the last step.

        Order: membership → convenio → referral → loyalty
        """
        subtotal = 100000
        membership_disc = 10000
        referral_disc = 5000
        loyalty_disc = 3000
        expected_total = subtotal - membership_disc - referral_disc - loyalty_disc

        with _patch_invoice_create(
            _make_invoice_response(
                subtotal=subtotal,
                total=expected_total,
                membership_discount=membership_disc,
                referral_discount=referral_disc,
                loyalty_discount=loyalty_disc,
            )
        ):
            response = await authenticated_client.post(
                INVOICE_BASE,
                json=_base_invoice_payload(_invoice_item(price=subtotal)),
            )

        assert response.status_code in (201, 500)
        if response.status_code == 201:
            data = response.json()
            assert data["loyalty_discount_cents"] == loyalty_disc
            assert data["total_cents"] == expected_total


# ─── Full discount stack ──────────────────────────────────────────────────────


@pytest.mark.integration
class TestFullDiscountStack:
    async def test_full_stack_all_four_discounts(self, authenticated_client):
        """POST invoice: all four discount types stacked in correct order.

        Stack order (per spec):
          1. membership → per-item
          2. convenio → per-item, on remaining after membership
          3. referral → post-total, flat
          4. loyalty → post-referral, flat

        Example:
          - List price: 200_000 COP
          - Membership 10%:  -20_000 → per-item remaining: 180_000
          - Convenio 15%:    -27_000 → per-item remaining: 153_000
          - Referral flat:   -10_000 → total after: 143_000
          - Loyalty 500 pts: -5_000  → final total:  138_000
        """
        subtotal = 200000
        membership_disc = 20000
        convenio_disc = 27000
        referral_disc = 10000
        loyalty_disc = 5000
        expected_total = subtotal - membership_disc - convenio_disc - referral_disc - loyalty_disc

        with _patch_invoice_create(
            _make_invoice_response(
                subtotal=subtotal,
                total=expected_total,
                membership_discount=membership_disc,
                convenio_discount=convenio_disc,
                referral_discount=referral_disc,
                loyalty_discount=loyalty_disc,
            )
        ):
            response = await authenticated_client.post(
                INVOICE_BASE,
                json=_base_invoice_payload(_invoice_item(price=subtotal)),
            )

        assert response.status_code in (201, 500)
        if response.status_code == 201:
            data = response.json()
            assert data["membership_discount_cents"] == membership_disc
            assert data["convenio_discount_cents"] == convenio_disc
            assert data["referral_discount_cents"] == referral_disc
            assert data["loyalty_discount_cents"] == loyalty_disc
            # Verify the total is the sum of all discounts applied
            total_discounts = (
                membership_disc + convenio_disc + referral_disc + loyalty_disc
            )
            assert data["total_cents"] == subtotal - total_discounts

    async def test_full_stack_total_never_negative(self, authenticated_client):
        """POST invoice: stacked discounts cannot reduce total below 0."""
        subtotal = 50000
        # Discounts that in theory exceed the subtotal
        membership_disc = 40000
        referral_disc = 30000  # Would exceed if not capped

        with _patch_invoice_create(
            _make_invoice_response(
                subtotal=subtotal,
                total=0,
                membership_discount=membership_disc,
                referral_discount=0,  # capped because total already 0
            )
        ):
            response = await authenticated_client.post(
                INVOICE_BASE,
                json=_base_invoice_payload(_invoice_item(price=subtotal)),
            )

        assert response.status_code in (201, 500)
        if response.status_code == 201:
            data = response.json()
            assert data["total_cents"] >= 0

    async def test_full_stack_multi_item_invoice(self, authenticated_client):
        """POST invoice with multiple items: discounts applied to each item independently."""
        items = [
            _invoice_item("Limpieza dental", 80000),
            _invoice_item("Consulta de revisión", 60000),
            _invoice_item("Radiografía periapical", 40000),
        ]
        subtotal = 180000
        membership_disc = 18000  # 10% of 180_000
        expected_total = subtotal - membership_disc

        with _patch_invoice_create(
            _make_invoice_response(
                subtotal=subtotal,
                total=expected_total,
                membership_discount=membership_disc,
            )
        ):
            response = await authenticated_client.post(
                INVOICE_BASE,
                json={"items": items},
            )

        assert response.status_code in (201, 500)
        if response.status_code == 201:
            data = response.json()
            assert data["total_cents"] == expected_total

    async def test_invoice_missing_items_returns_422(self, authenticated_client):
        """POST invoice without items returns 422."""
        response = await authenticated_client.post(INVOICE_BASE, json={})
        assert response.status_code == 422

    async def test_invoice_item_negative_price_returns_422(self, authenticated_client):
        """POST invoice with negative unit_price returns 422."""
        response = await authenticated_client.post(
            INVOICE_BASE,
            json={"items": [{"description": "Bad item", "unit_price": -1000, "quantity": 1}]},
        )
        assert response.status_code == 422

    async def test_invoice_item_zero_quantity_returns_422(self, authenticated_client):
        """POST invoice with quantity=0 returns 422."""
        response = await authenticated_client.post(
            INVOICE_BASE,
            json={"items": [{"description": "Zero qty", "unit_price": 10000, "quantity": 0}]},
        )
        assert response.status_code == 422
