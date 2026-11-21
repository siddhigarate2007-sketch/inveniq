"""User authentication, role definitions, and audit schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """Role-Based Access Control (RBAC) user roles."""

    BUYER = "buyer"
    ANALYST = "analyst"
    FINANCE_APPROVER = "finance_approver"
    ADMIN = "admin"


class User(BaseModel):
    """System user entity."""

    user_id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserInDB(User):
    """User entity stored in database with hashed password."""

    hashed_password: str


class LoginRequest(BaseModel):
    """Login credentials payload."""

    email: str
    password: str


class Token(BaseModel):
    """JWT bearer token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = 86400
    user: User


class TokenData(BaseModel):
    """Payload decoded from JWT."""

    user_id: str
    email: str
    role: UserRole


class AuditLogEntry(BaseModel):
    """Immutable audit trail record for compliance and governance."""

    audit_id: str
    user_id: str
    user_email: str
    user_role: UserRole
    action: str = Field(..., description="E.g., SUBMIT_RUN, APPROVE_RUN, REJECT_RUN, MODIFY_CONSTRAINTS")
    target_type: str = Field(..., description="OPTIMIZATION_RUN, INVENTORY_ITEM, CONTRACT")
    target_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: dict[str, Any] = Field(default_factory=dict)
