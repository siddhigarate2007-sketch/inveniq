"""Audit log inspection endpoints."""

from fastapi import APIRouter, Depends, Query
from inveniq_api.auth.rbac import require_roles
from inveniq_core.db_store import db_store
from inveniq_core.schemas.user import AuditLogEntry, User, UserRole

router = APIRouter(prefix="/audit", tags=["Governance & Audit"])


@router.get("/logs", response_model=list[AuditLogEntry])
async def get_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles([UserRole.FINANCE_APPROVER, UserRole.ADMIN, UserRole.ANALYST])),
) -> list[AuditLogEntry]:
    """Retrieves immutable audit trail of submissions, reviews, and financial approvals."""
    return db_store.list_audit_logs(limit=limit)
