import pytest
from jose import JWTError

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_pre_auth_token,
    create_refresh_token,
    decode_access_token,
    decode_pre_auth_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


@pytest.mark.unit
class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("MyPassword1")
        assert verify_password("MyPassword1", hashed)
        assert not verify_password("WrongPassword", hashed)

    def test_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt salts differ


@pytest.mark.unit
class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token(
            user_id="user123",
            tenant_id="tenant456",
            role="doctor",
            permissions=["patients:read"],
            email="doc@test.co",
            name="Dr Test",
        )
        payload = decode_access_token(token)
        assert payload["sub"] == "usr_user123"
        assert payload["tid"] == "tn_tenant456"
        assert payload["role"] == "doctor"
        assert "patients:read" in payload["perms"]
        assert payload["iss"] == settings.jwt_issuer
        assert payload["aud"] == settings.jwt_audience

    def test_invalid_token_raises(self):
        with pytest.raises(JWTError):
            decode_access_token("invalid.token.here")

    def test_pre_auth_token(self):
        token = create_pre_auth_token(user_id="u1", email="test@t.co")
        payload = decode_pre_auth_token(token)
        assert payload["sub"] == "usr_u1"
        assert payload["type"] == "pre_auth"


@pytest.mark.unit
class TestRefreshToken:
    def test_create_returns_pair(self):
        raw, hashed = create_refresh_token()
        assert len(raw) == 36  # UUID format
        assert len(hashed) == 64  # SHA-256 hex

    def test_hash_matches(self):
        raw, hashed = create_refresh_token()
        assert hash_refresh_token(raw) == hashed

    def test_different_tokens(self):
        raw1, _ = create_refresh_token()
        raw2, _ = create_refresh_token()
        assert raw1 != raw2
