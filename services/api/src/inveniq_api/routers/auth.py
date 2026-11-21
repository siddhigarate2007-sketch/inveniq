"""Authentication endpoints: login and user profile."""

from fastapi import APIRouter, Depends, HTTPException, status
from inveniq_api.auth.jwt import create_access_token
from inveniq_api.auth.rbac import get_current_user
from inveniq_core.db_store import db_store, hash_password
from inveniq_core.schemas.user import LoginRequest, Token, User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest) -> Token:
    """Authenticates user credentials and returns signed JWT access token."""
    user = db_store.get_user_by_email(payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    expected_hash = hash_password(payload.password)
    if user.hashed_password != expected_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
    )

    clean_user = User(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )

    return Token(access_token=token, user=clean_user)


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Returns the authenticated user profile and active role."""
    return current_user
