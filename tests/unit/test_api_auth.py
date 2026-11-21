"""Unit tests for API authentication and JWT tokens."""

from inveniq_api.auth.jwt import create_access_token, decode_access_token
from inveniq_core.db_store import hash_password
from inveniq_core.schemas.user import UserRole


def test_jwt_token_encode_decode() -> None:
    token = create_access_token(
        user_id="USR_001",
        email="test@tbo.com",
        role=UserRole.BUYER,
    )
    assert isinstance(token, str)
    assert len(token) > 20

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded.user_id == "USR_001"
    assert decoded.email == "test@tbo.com"
    assert decoded.role == UserRole.BUYER


def test_password_hashing() -> None:
    pwd = "MySecretPassword123"
    h1 = hash_password(pwd)
    h2 = hash_password(pwd)
    assert h1 == h2
    assert h1 != hash_password("OtherPassword")
