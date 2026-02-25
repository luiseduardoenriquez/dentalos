"""Unit tests for tenant Pydantic schemas.

Covers TenantCreateRequest, TenantUpdateRequest, TenantSettingsUpdate,
and OnboardingStepRequest validation behavior.
"""
import pytest
from pydantic import ValidationError

from app.schemas.tenant import (
    OnboardingStepRequest,
    TenantCreateRequest,
    TenantSettingsUpdate,
    TenantUpdateRequest,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _valid_create(**overrides) -> dict:
    base = {
        "name": "Clínica del Norte",
        "owner_email": "owner@clinica.co",
        "country_code": "CO",
        "plan_id": "550e8400-e29b-41d4-a716-446655440000",
    }
    base.update(overrides)
    return base


# ─── TenantCreateRequest ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestTenantCreateRequest:
    def test_valid_minimal(self):
        req = TenantCreateRequest(**_valid_create())
        assert req.name == "Clínica del Norte"
        assert req.country_code == "CO"

    def test_email_normalized_lowercase(self):
        req = TenantCreateRequest(**_valid_create(owner_email="Owner@CLINICA.CO"))
        assert req.owner_email == "owner@clinica.co"

    def test_email_normalized_strips_whitespace(self):
        req = TenantCreateRequest(**_valid_create(owner_email="  owner@clinica.co  "))
        assert req.owner_email == "owner@clinica.co"

    def test_name_stripped(self):
        req = TenantCreateRequest(**_valid_create(name="  Mi Clínica  "))
        assert req.name == "Mi Clínica"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            TenantCreateRequest(**_valid_create(owner_email="not-an-email"))

    def test_valid_country_codes(self):
        for code in ("CO", "MX", "CL", "AR", "PE", "EC"):
            req = TenantCreateRequest(**_valid_create(country_code=code))
            assert req.country_code == code

    def test_invalid_country_code_raises(self):
        with pytest.raises(ValidationError):
            TenantCreateRequest(**_valid_create(country_code="US"))

    def test_invalid_country_code_lowercase_raises(self):
        with pytest.raises(ValidationError):
            TenantCreateRequest(**_valid_create(country_code="co"))

    def test_valid_phone_accepted(self):
        req = TenantCreateRequest(**_valid_create(phone="+573001234567"))
        assert req.phone == "+573001234567"

    def test_phone_without_plus_accepted(self):
        req = TenantCreateRequest(**_valid_create(phone="3001234567"))
        assert req.phone == "3001234567"

    def test_invalid_phone_raises(self):
        with pytest.raises(ValidationError):
            TenantCreateRequest(**_valid_create(phone="abc-not-a-phone"))

    def test_phone_is_optional(self):
        req = TenantCreateRequest(**_valid_create())
        assert req.phone is None

    def test_name_too_short_raises(self):
        with pytest.raises(ValidationError):
            TenantCreateRequest(**_valid_create(name=""))

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            TenantCreateRequest(**_valid_create(name="x" * 201))

    def test_missing_plan_id_raises(self):
        data = _valid_create()
        del data["plan_id"]
        with pytest.raises(ValidationError):
            TenantCreateRequest(**data)


# ─── TenantUpdateRequest ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestTenantUpdateRequest:
    def test_all_fields_optional_empty_payload_valid(self):
        req = TenantUpdateRequest()
        assert req.name is None
        assert req.country_code is None
        assert req.timezone is None
        assert req.currency_code is None
        assert req.phone is None
        assert req.address is None
        assert req.logo_url is None
        assert req.plan_id is None

    def test_partial_update_name_only(self):
        req = TenantUpdateRequest(name="Nueva Clínica")
        assert req.name == "Nueva Clínica"
        assert req.country_code is None

    def test_name_stripped(self):
        req = TenantUpdateRequest(name="  Clínica Sur  ")
        assert req.name == "Clínica Sur"

    def test_valid_country_code(self):
        req = TenantUpdateRequest(country_code="MX")
        assert req.country_code == "MX"

    def test_invalid_country_code_raises(self):
        with pytest.raises(ValidationError):
            TenantUpdateRequest(country_code="BR")

    def test_currency_code_three_uppercase_letters(self):
        req = TenantUpdateRequest(currency_code="COP")
        assert req.currency_code == "COP"

    def test_currency_code_lowercase_raises(self):
        with pytest.raises(ValidationError):
            TenantUpdateRequest(currency_code="cop")

    def test_currency_code_too_short_raises(self):
        with pytest.raises(ValidationError):
            TenantUpdateRequest(currency_code="CO")

    def test_currency_code_too_long_raises(self):
        with pytest.raises(ValidationError):
            TenantUpdateRequest(currency_code="COPX")

    def test_valid_phone(self):
        req = TenantUpdateRequest(phone="+573001234567")
        assert req.phone == "+573001234567"

    def test_invalid_phone_raises(self):
        with pytest.raises(ValidationError):
            TenantUpdateRequest(phone="not-a-phone")

    def test_address_and_logo_url_stored(self):
        req = TenantUpdateRequest(address="Calle 123, Bogotá", logo_url="https://cdn.test/logo.png")
        assert req.address == "Calle 123, Bogotá"
        assert req.logo_url == "https://cdn.test/logo.png"


# ─── TenantSettingsUpdate ────────────────────────────────────────────────────

@pytest.mark.unit
class TestTenantSettingsUpdate:
    def test_all_fields_optional(self):
        req = TenantSettingsUpdate()
        assert req.name is None
        assert req.phone is None
        assert req.settings is None

    def test_name_stripped(self):
        req = TenantSettingsUpdate(name="  Clínica Dental  ")
        assert req.name == "Clínica Dental"

    def test_currency_code_pattern_enforced(self):
        req = TenantSettingsUpdate(currency_code="USD")
        assert req.currency_code == "USD"

    def test_currency_code_invalid_raises(self):
        with pytest.raises(ValidationError):
            TenantSettingsUpdate(currency_code="us")

    def test_phone_pattern_enforced(self):
        with pytest.raises(ValidationError):
            TenantSettingsUpdate(phone="abc")

    def test_partial_settings_dict_accepted(self):
        req = TenantSettingsUpdate(settings={"appointment_reminder_hours": 24, "invoice_prefix": "FAC"})
        assert req.settings["appointment_reminder_hours"] == 24

    def test_empty_settings_dict_accepted(self):
        req = TenantSettingsUpdate(settings={})
        assert req.settings == {}

    def test_locale_stored(self):
        req = TenantSettingsUpdate(locale="es-CO")
        assert req.locale == "es-CO"

    def test_locale_too_long_raises(self):
        with pytest.raises(ValidationError):
            TenantSettingsUpdate(locale="es-CO-really-too-long-for-this-field")


# ─── OnboardingStepRequest ───────────────────────────────────────────────────

@pytest.mark.unit
class TestOnboardingStepRequest:
    def test_valid_step_zero(self):
        req = OnboardingStepRequest(step=0, data={"clinic_name": "Test"})
        assert req.step == 0

    def test_valid_step_four(self):
        req = OnboardingStepRequest(step=4, data={"completed": True})
        assert req.step == 4

    def test_step_below_zero_raises(self):
        with pytest.raises(ValidationError):
            OnboardingStepRequest(step=-1, data={})

    def test_step_above_four_raises(self):
        with pytest.raises(ValidationError):
            OnboardingStepRequest(step=5, data={})

    def test_data_dict_is_required(self):
        with pytest.raises(ValidationError):
            OnboardingStepRequest(step=1)

    def test_data_stored_as_provided(self):
        payload = {"specialty": "ortodoncia", "doctors": 2}
        req = OnboardingStepRequest(step=2, data=payload)
        assert req.data["specialty"] == "ortodoncia"
        assert req.data["doctors"] == 2

    def test_empty_data_dict_accepted(self):
        req = OnboardingStepRequest(step=0, data={})
        assert req.data == {}

    def test_all_steps_in_range_valid(self):
        for step in range(5):
            req = OnboardingStepRequest(step=step, data={})
            assert req.step == step
