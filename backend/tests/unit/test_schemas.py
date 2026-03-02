from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.patient import PatientCreate, PatientUpdate
from app.schemas.user import UserProfileUpdate, UserTeamMemberUpdate


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


@pytest.mark.unit
class TestUserProfileUpdate:
    def test_valid_name_only(self):
        u = UserProfileUpdate(name="Dr. García")
        assert u.name == "Dr. García"

    def test_invalid_phone(self):
        with pytest.raises(ValidationError):
            UserProfileUpdate(phone="not-a-phone")

    def test_name_stripped(self):
        u = UserProfileUpdate(name="  Dr. García  ")
        assert u.name == "Dr. García"

    def test_specialties_stripped(self):
        u = UserProfileUpdate(specialties=["  ortodoncia  ", " ", "endodoncia"])
        assert u.specialties == ["ortodoncia", "endodoncia"]

    def test_valid_phone(self):
        u = UserProfileUpdate(phone="+573001234567")
        assert u.phone == "+573001234567"

    def test_all_none_valid(self):
        u = UserProfileUpdate()
        assert u.name is None
        assert u.phone is None


@pytest.mark.unit
class TestUserTeamMemberUpdate:
    def test_valid_role_doctor(self):
        u = UserTeamMemberUpdate(role="doctor")
        assert u.role == "doctor"

    def test_valid_role_assistant(self):
        u = UserTeamMemberUpdate(role="assistant")
        assert u.role == "assistant"

    def test_valid_role_receptionist(self):
        u = UserTeamMemberUpdate(role="receptionist")
        assert u.role == "receptionist"

    def test_invalid_role_superadmin(self):
        with pytest.raises(ValidationError):
            UserTeamMemberUpdate(role="superadmin")

    def test_invalid_role_clinic_owner(self):
        with pytest.raises(ValidationError):
            UserTeamMemberUpdate(role="clinic_owner")

    def test_invalid_role_random(self):
        with pytest.raises(ValidationError):
            UserTeamMemberUpdate(role="janitor")

    def test_empty_update_valid(self):
        u = UserTeamMemberUpdate()
        assert u.role is None
        assert u.is_active is None


@pytest.mark.unit
class TestPatientCreate:
    def test_valid_minimal(self):
        p = PatientCreate(
            document_type="CC",
            document_number="1234567890",
            first_name="Juan",
            last_name="Pérez",
        )
        assert p.document_type == "CC"
        assert p.first_name == "Juan"

    def test_valid_full(self):
        p = PatientCreate(
            document_type="CE",
            document_number="ABC-123",
            first_name="María",
            last_name="López",
            birthdate=date(1990, 5, 15),
            gender="female",
            phone="+573001234567",
            email="maria@test.co",
            address="Calle 100 #15-20",
            city="Bogotá",
            blood_type="O+",
            allergies=["penicilina"],
        )
        assert p.gender == "female"
        assert p.blood_type == "O+"

    def test_invalid_document_type(self):
        with pytest.raises(ValidationError):
            PatientCreate(
                document_type="DNI",
                document_number="123456",
                first_name="Juan",
                last_name="Pérez",
            )

    def test_invalid_phone(self):
        with pytest.raises(ValidationError):
            PatientCreate(
                document_type="CC",
                document_number="123456",
                first_name="Juan",
                last_name="Pérez",
                phone="not-a-phone",
            )

    def test_future_birthdate(self):
        with pytest.raises(ValidationError, match="future"):
            PatientCreate(
                document_type="CC",
                document_number="123456",
                first_name="Juan",
                last_name="Pérez",
                birthdate=date.today() + timedelta(days=1),
            )

    def test_blank_first_name(self):
        with pytest.raises(ValidationError, match="blank"):
            PatientCreate(
                document_type="CC",
                document_number="123456",
                first_name="   ",
                last_name="Pérez",
            )

    def test_invalid_blood_type(self):
        with pytest.raises(ValidationError):
            PatientCreate(
                document_type="CC",
                document_number="123456",
                first_name="Juan",
                last_name="Pérez",
                blood_type="X+",
            )

    def test_invalid_gender(self):
        with pytest.raises(ValidationError):
            PatientCreate(
                document_type="CC",
                document_number="123456",
                first_name="Juan",
                last_name="Pérez",
                gender="unknown",
            )

    def test_email_normalized(self):
        p = PatientCreate(
            document_type="CC",
            document_number="123456",
            first_name="Juan",
            last_name="Pérez",
            email="TEST@CLINIC.CO",
        )
        assert p.email == "test@clinic.co"

    def test_allergies_stripped(self):
        p = PatientCreate(
            document_type="CC",
            document_number="123456",
            first_name="Juan",
            last_name="Pérez",
            allergies=["  pollen  ", " ", "latex"],
        )
        assert p.allergies == ["pollen", "latex"]


@pytest.mark.unit
class TestPatientUpdate:
    def test_empty_update_valid(self):
        p = PatientUpdate()
        assert p.first_name is None
        assert p.phone is None

    def test_partial_fields(self):
        p = PatientUpdate(first_name="Updated")
        assert p.first_name == "Updated"

    def test_invalid_phone(self):
        with pytest.raises(ValidationError):
            PatientUpdate(phone="bad")

    def test_invalid_document_type(self):
        with pytest.raises(ValidationError):
            PatientUpdate(document_type="DNI")
