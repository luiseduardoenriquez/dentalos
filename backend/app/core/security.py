"""Security utilities — RS256 JWT tokens and password hashing."""
import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger("dentalos.security")


# ─── Password hashing ───────────────────────────────


def hash_password(password: str) -> str:
    """Hash a password with bcrypt + optional pepper."""
    salted = password + settings.password_pepper if settings.password_pepper else password
    salt = bcrypt.gensalt(rounds=settings.password_bcrypt_rounds)
    return bcrypt.hashpw(salted.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    salted = (
        plain_password + settings.password_pepper
        if settings.password_pepper
        else plain_password
    )
    return bcrypt.checkpw(salted.encode("utf-8"), hashed_password.encode("utf-8"))


# ─── RS256 Key management (lazy loading) ──────────────

_private_key: str | None = None
_public_key: str | None = None


def _load_private_key() -> str:
    global _private_key  # noqa: PLW0603
    if _private_key is None:
        key_path = Path(settings.jwt_private_key_path)
        if not key_path.exists():
            raise FileNotFoundError(f"JWT private key not found: {key_path}")
        _private_key = key_path.read_text()
    return _private_key


def _load_public_key() -> str:
    global _public_key  # noqa: PLW0603
    if _public_key is None:
        key_path = Path(settings.jwt_public_key_path)
        if not key_path.exists():
            raise FileNotFoundError(f"JWT public key not found: {key_path}")
        _public_key = key_path.read_text()
    return _public_key


def set_keys(
    private_key: str | None = None, public_key: str | None = None
) -> None:
    """Inject keys directly (for testing)."""
    global _private_key, _public_key  # noqa: PLW0603
    if private_key is not None:
        _private_key = private_key
    if public_key is not None:
        _public_key = public_key


def clear_keys() -> None:
    """Reset cached keys (for testing)."""
    global _private_key, _public_key  # noqa: PLW0603
    _private_key = None
    _public_key = None


# ─── JWT Access Tokens ───────────────────────────────


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    permissions: list[str],
    email: str,
    name: str,
    token_version: int = 0,
) -> str:
    """Create an RS256 JWT access token with full claims."""
    now = datetime.now(UTC)
    jti = f"tok_{uuid.uuid4().hex}"
    payload: dict[str, Any] = {
        "sub": f"usr_{user_id}",
        "tid": f"tn_{tenant_id}" if not tenant_id.startswith("tn_") else tenant_id,
        "role": role,
        "perms": permissions,
        "email": email,
        "name": name,
        "tver": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": jti,
    }
    headers = {"kid": settings.jwt_key_id}
    return jwt.encode(
        payload,
        _load_private_key(),
        algorithm=settings.jwt_algorithm,
        headers=headers,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an RS256 JWT access token.

    Raises JWTError on invalid/expired tokens.
    """
    return jwt.decode(
        token,
        _load_public_key(),
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )


# ─── Refresh Tokens ──────────────────────────────────


def create_refresh_token() -> tuple[str, str]:
    """Create a refresh token.

    Returns (raw_token, sha256_hash) — store hash in DB, send raw to client.
    """
    raw = str(uuid.uuid4())
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_refresh_token(raw_token: str) -> str:
    """Hash a raw refresh token for DB lookup."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


# ─── Portal JWT Tokens ───────────────────────────────


def create_portal_access_token(
    patient_id: str,
    tenant_id: str,
    email: str,
    name: str,
) -> str:
    """Create an RS256 JWT access token for portal patients.

    Portal tokens use scope='portal' and sub='pat_{patient_id}' to clearly
    distinguish them from staff tokens (scope is absent, sub='usr_{user_id}').
    Portal access tokens have a 30-minute TTL (longer than staff 15min since
    patients are less frequent users).
    """
    now = datetime.now(UTC)
    jti = f"ptok_{uuid.uuid4().hex}"
    payload: dict[str, Any] = {
        "sub": f"pat_{patient_id}",
        "tid": f"tn_{tenant_id}" if not tenant_id.startswith("tn_") else tenant_id,
        "scope": "portal",
        "role": "patient",
        "pid": patient_id,
        "email": email,
        "name": name,
        "iat": now,
        "exp": now + timedelta(minutes=30),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": jti,
    }
    headers = {"kid": settings.jwt_key_id}
    return jwt.encode(
        payload,
        _load_private_key(),
        algorithm=settings.jwt_algorithm,
        headers=headers,
    )


def create_portal_refresh_token() -> tuple[str, str]:
    """Create a portal refresh token.

    Returns (raw_token, sha256_hash). Uses 'portal:' prefix to distinguish
    from staff refresh tokens in Redis/DB storage.
    """
    raw = f"portal:{uuid.uuid4()}"
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


# ─── Pre-auth tokens (multi-tenant selection) ────────


def create_pre_auth_token(user_id: str, email: str) -> str:
    """Create a short-lived token for tenant selection (5 min)."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": f"usr_{user_id}",
        "email": email,
        "type": "pre_auth",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": settings.jwt_issuer,
    }
    return jwt.encode(
        payload, _load_private_key(), algorithm=settings.jwt_algorithm
    )


def decode_pre_auth_token(token: str) -> dict[str, Any]:
    """Decode a pre-auth token for tenant selection."""
    payload = jwt.decode(
        token,
        _load_public_key(),
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        options={"verify_aud": False},
    )
    if payload.get("type") != "pre_auth":
        raise JWTError("Not a pre-auth token")
    return payload
