"""Security helpers: password hashing (Argon2) and JWT issuance/validation."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

try:  # pwdlib >= 0.3 (module layout changed)
    from pwdlib.hashers.argon2 import Argon2Hasher as _Argon2Hasher
except ImportError:  # pragma: no cover - pwdlib < 0.3
    from pwdlib.strategies.argon2 import Argon2Strategy as _Argon2Hasher

# Single shared hasher for the process.
_password_hasher = PasswordHash((_Argon2Hasher(),))

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2."""
    return _password_hasher.hash(password)


def verify_password(plaintext: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored Argon2 hash."""
    try:
        return _password_hasher.verify(plaintext, password_hash)
    except Exception:
        return False


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Build and sign a JWT."""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a short-lived access JWT."""
    return _create_token(
        subject,
        ACCESS_TOKEN_TYPE,
        timedelta(minutes=settings.access_token_expire_minutes),
        extra_claims,
    )


def create_refresh_token(subject: str) -> str:
    """Create a long-lived refresh JWT."""
    return _create_token(
        subject,
        REFRESH_TOKEN_TYPE,
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """Decode and validate a JWT, raising 401 on any failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token has expired.", code="TOKEN_EXPIRED")
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid token.", code="TOKEN_INVALID")

    if expected_type and payload.get("type") != expected_type:
        raise UnauthorizedException("Invalid token type.", code="TOKEN_INVALID")

    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedException("Token missing subject.", code="TOKEN_INVALID")

    return payload
