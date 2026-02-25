import uuid

import pytest

from app.models.public.plan import Plan
from app.models.public.tenant import Tenant
from app.models.public.user_tenant_membership import UserTenantMembership


@pytest.mark.unit
class TestPlanModel:
    def test_instantiation(self):
        plan = Plan(name="Free", slug="free", max_patients=50, is_active=True)
        assert plan.name == "Free"
        assert plan.slug == "free"
        assert plan.max_patients == 50

    def test_repr(self):
        plan = Plan(name="Free", slug="free")
        assert "Free" in repr(plan)


@pytest.mark.unit
class TestTenantModel:
    def test_instantiation(self):
        tenant = Tenant(
            slug="test-clinic",
            schema_name="tn_abcd1234",
            name="Test Clinic",
            plan_id=uuid.uuid4(),
            owner_email="test@test.co",
            status="pending",
            country_code="CO",
        )
        assert tenant.name == "Test Clinic"
        assert tenant.status == "pending"
        assert tenant.country_code == "CO"

    def test_repr(self):
        tenant = Tenant(
            slug="test", schema_name="tn_12345678",
            name="My Clinic", plan_id=uuid.uuid4(),
            owner_email="t@t.co",
        )
        assert "My Clinic" in repr(tenant)


@pytest.mark.unit
class TestMembershipModel:
    def test_instantiation(self):
        m = UserTenantMembership(
            user_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            role="doctor",
            is_primary=False,
            status="active",
        )
        assert m.role == "doctor"
        assert m.is_primary is False
        assert m.status == "active"
