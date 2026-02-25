import pytest

from app.core.exceptions import TenantError
from app.core.tenant import (
    TenantContext,
    clear_current_tenant,
    get_current_tenant,
    get_current_tenant_or_raise,
    set_current_tenant,
    validate_schema_name,
)


@pytest.mark.unit
class TestTenantContext:
    def test_set_and_get(self):
        ctx = TenantContext(
            tenant_id="abc",
            schema_name="tn_abcdef01",
            plan_id="p1",
            plan_name="Free",
            country_code="CO",
            timezone="America/Bogota",
            currency_code="COP",
            status="active",
        )
        set_current_tenant(ctx)
        assert get_current_tenant() is ctx
        clear_current_tenant()
        assert get_current_tenant() is None

    def test_get_or_raise_when_none(self):
        clear_current_tenant()
        with pytest.raises(TenantError):
            get_current_tenant_or_raise()

    def test_frozen(self):
        ctx = TenantContext(
            tenant_id="abc",
            schema_name="tn_abcdef01",
            plan_id="p1",
            plan_name="Free",
            country_code="CO",
            timezone="America/Bogota",
            currency_code="COP",
            status="active",
        )
        with pytest.raises(AttributeError):
            ctx.tenant_id = "changed"


@pytest.mark.unit
class TestSchemaValidation:
    @pytest.mark.parametrize(
        "name,valid",
        [
            ("tn_abcdef01", True),
            ("tn_1234abcd", True),
            ("tn_abcdef0123", True),
            ("tn_abc", False),           # too short
            ("tn_ABCDEF01", False),      # uppercase
            ("public", False),
            ("tn_", False),
            ("tn_abcdef01_extra", False),
            ("", False),
        ],
    )
    def test_validate_schema_name(self, name, valid):
        assert validate_schema_name(name) == valid
