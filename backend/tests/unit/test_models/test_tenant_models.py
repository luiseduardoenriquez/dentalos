import uuid
from datetime import UTC, datetime

import pytest

from app.models.tenant.user import User
from app.models.tenant.user_invite import UserInvite
from app.models.tenant.user_session import UserSession


@pytest.mark.unit
class TestUserModel:
    def test_instantiation(self):
        user = User(
            email="doc@test.co",
            password_hash="hash",
            name="Dr Test",
            role="doctor",
            is_active=True,
            email_verified=False,
            failed_login_attempts=0,
        )
        assert user.email == "doc@test.co"
        assert user.role == "doctor"
        assert user.is_active is True
        assert user.email_verified is False
        assert user.failed_login_attempts == 0


@pytest.mark.unit
class TestUserSessionModel:
    def test_instantiation(self):
        session = UserSession(
            user_id=uuid.uuid4(),
            refresh_token_hash="a" * 64,
            expires_at=datetime.now(UTC),
            is_revoked=False,
        )
        assert session.is_revoked is False
        assert len(session.refresh_token_hash) == 64


@pytest.mark.unit
class TestUserInviteModel:
    def test_instantiation(self):
        invite = UserInvite(
            email="new@test.co",
            role="doctor",
            invited_by=uuid.uuid4(),
            token_hash="b" * 64,
            expires_at=datetime.now(UTC),
            status="pending",
        )
        assert invite.status == "pending"
        assert invite.role == "doctor"
