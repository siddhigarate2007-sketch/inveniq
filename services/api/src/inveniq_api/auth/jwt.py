"""JWT authentication utilities for InvenIQ."""

from datetime import datetime, timedelta
from typing import Any
import jwt
from inveniq_core.config import settings
from inveniq_core.schemas.user import TokenData, UserRole

ALGORITHM = "HS256"


def create_access_token(
    user_id: str,
    email: str,
    role: UserRole,
    expires_delta: timedelta | None = None,
) -> str:
    """Generates a cryptographically signed JWT access token."""
    delta = expires_delta or timedelta(days=1)
    expire = datetime.utcnow() + delta
    payload = {
        "sub": user_id,
        "email": email,
        "role": role.value,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    return str(encoded)


def decode_access_token(token: str) -> TokenData | None:
    """Decodes and validates a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        role_str = payload.get("role")
        if not user_id or not email or not role_str:
            return None
        return TokenData(
            user_id=user_id,
            email=email,
            role=UserRole(role_str),
        )
    except Exception:
        return None
