"""Role-Based Access Control (RBAC) dependencies for FastAPI routes."""

from typing import Callable
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from inveniq_api.auth.jwt import decode_access_token
from inveniq_core.db_store import db_store
from inveniq_core.schemas.user import User, UserRole

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> User:
    """Dependency that extracts and authenticates current user from Bearer JWT."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = decode_access_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_db = db_store.get_user_by_id(token_data.user_id)
    if not user_db or not user_db.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return User(
        user_id=user_db.user_id,
        email=user_db.email,
        full_name=user_db.full_name,
        role=user_db.role,
        is_active=user_db.is_active,
        created_at=user_db.created_at,
    )


def require_roles(allowed_roles: list[UserRole]) -> Callable[[User], User]:
    """Dependency factory checking that the authenticated user possesses an allowed role."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of {[r.value for r in allowed_roles]}. Current role: {current_user.role.value}",
            )
        return current_user

    return role_checker
