import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest


@pytest.mark.unit
class TestRegisterRequest:
    def test_valid(self):
        r = RegisterRequest(
            email="test@clinica.co",
            password="TestPass1",
            name="Dr Test",
            clinic_name="Mi Clinica",
            country="CO",
        )
        assert r.email == "test@clinica.co"
        assert r.country == "CO"

    def test_email_normalized(self):
        r = RegisterRequest(
            email="  TEST@Clinica.Co  ",
            password="TestPass1",
            name="Dr Test",
            clinic_name="Mi Clinica",
            country="CO",
        )
        assert r.email == "test@clinica.co"

    def test_weak_password_no_uppercase(self):
        with pytest.raises(ValidationError, match="uppercase"):
            RegisterRequest(
                email="t@t.co",
                password="testpass1",
                name="T",
                clinic_name="C",
                country="CO",
            )

    def test_weak_password_no_digit(self):
        with pytest.raises(ValidationError, match="digit"):
            RegisterRequest(
                email="t@t.co",
                password="TestPass",
                name="T",
                clinic_name="C",
                country="CO",
            )

    def test_short_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="t@t.co",
                password="Tp1",
                name="T",
                clinic_name="C",
                country="CO",
            )

    def test_invalid_country(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="t@t.co",
                password="TestPass1",
                name="T",
                clinic_name="C",
                country="US",
            )

    def test_valid_phone(self):
        r = RegisterRequest(
            email="t@t.co",
            password="TestPass1",
            name="T",
            clinic_name="C",
            country="CO",
            phone="+573001234567",
        )
        assert r.phone == "+573001234567"


@pytest.mark.unit
class TestLoginRequest:
    def test_valid(self):
        r = LoginRequest(email="test@t.co", password="pass")
        assert r.email == "test@t.co"

    def test_email_normalized(self):
        r = LoginRequest(email="  TEST@T.CO  ", password="pass")
        assert r.email == "test@t.co"
