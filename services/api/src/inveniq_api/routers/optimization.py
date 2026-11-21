"""Optimization endpoints: run submission, polling, and financial approvals."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from inveniq_api.auth.rbac import get_current_user, require_roles
from inveniq_api.worker.job_runner import JobRunner
from inveniq_core.db_store import db_store
from inveniq_core.schemas.optimization import (
    ApprovalActionRequest,
    OptimizationRunRequest,
    OptimizationRunResponse,
    RunStatus,
)
from inveniq_core.schemas.user import User, UserRole

router = APIRouter(prefix="/optimization", tags=["Optimization"])


@router.post(
    "/runs",
    response_model=OptimizationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_optimization_run(
    request: OptimizationRunRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    current_user: User = Depends(require_roles([UserRole.BUYER, UserRole.ANALYST, UserRole.ADMIN])),
    sync: bool = Query(False, description="Run synchronously for fast integration tests"),
) -> OptimizationRunResponse:
    """Submits an asynchronous inventory optimization job. Supports idempotency keys."""
    run = JobRunner.dispatch_run(
        request=request,
        user_id=current_user.user_id,
        user_email=current_user.email,
        idempotency_key=x_idempotency_key,
        sync=sync,
    )
    return run


@router.get("/runs", response_model=list[OptimizationRunResponse])
async def list_optimization_runs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
) -> list[OptimizationRunResponse]:
    """Lists past optimization runs with status and metrics."""
    return db_store.list_runs(limit=limit, offset=offset)


@router.get("/runs/{run_id}", response_model=OptimizationRunResponse)
async def get_optimization_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
) -> OptimizationRunResponse:
    """Retrieves full details, recommendations, and status of an optimization run."""
    run = db_store.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization run {run_id} not found",
        )
    return run


@router.post("/runs/{run_id}/approve", response_model=OptimizationRunResponse)
async def approve_or_reject_run(
    run_id: str,
    payload: ApprovalActionRequest,
    current_user: User = Depends(require_roles([UserRole.FINANCE_APPROVER, UserRole.ADMIN])),
) -> OptimizationRunResponse:
    """Approves or rejects an optimization run. Restricted to Finance Approver / Admin roles."""
    run = db_store.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization run {run_id} not found",
        )

    if run.status not in (RunStatus.COMPLETED_AWAITING_APPROVAL, RunStatus.APPROVED, RunStatus.REJECTED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run cannot be approved in state {run.status.value}. Must be COMPLETED_AWAITING_APPROVAL.",
        )

    # Perform state transition
    action = "APPROVE_RUN" if payload.approved else "REJECT_RUN"
    run.status = RunStatus.APPROVED if payload.approved else RunStatus.REJECTED
    run.approver_user_id = current_user.user_id
    run.approver_notes = payload.notes
    run.approval_timestamp = datetime.utcnow()
    run.updated_at = datetime.utcnow()

    db_store.save_run(run)

    # Record permanent audit log
    db_store.record_audit(
        user_id=current_user.user_id,
        user_email=current_user.email,
        user_role=current_user.role,
        action=action,
        target_type="OPTIMIZATION_RUN",
        target_id=run_id,
        details={
            "approved": payload.approved,
            "notes": payload.notes,
            "budget_inr": run.budget_inr,
            "committed_inr": run.total_capital_committed_inr,
            "expected_profit_inr": run.expected_profit_inr,
        },
    )

    return run
