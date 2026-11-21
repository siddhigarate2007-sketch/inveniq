"""Pydantic v2 schemas for optimization requests, runs, recommendations, and risk simulations."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Lifecycle state transitions of an optimization run."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED_AWAITING_APPROVAL = "COMPLETED_AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class OptimizationRunRequest(BaseModel):
    """Payload to trigger an asynchronous stochastic optimization solve."""

    budget_inr: float = Field(..., gt=0, description="Available capital procurement budget in INR")
    risk_appetite: str = Field(default="BALANCED", description="CONSERVATIVE, BALANCED, or AGGRESSIVE")
    dest_exposure_cap: float = Field(default=0.35, ge=0.05, le=1.0, description="Max budget allocated to single destination")
    supplier_exposure_cap: float = Field(default=0.30, ge=0.05, le=1.0, description="Max budget allocated to single supplier")
    target_destination_ids: Optional[list[str]] = Field(default=None, description="Optional destination filter")
    notes: Optional[str] = Field(default=None, description="Procurement run business context")


class RecommendationItem(BaseModel):
    """Individual inventory buy recommendation output."""

    item_id: str
    destination_id: str
    product_type: str
    supplier_id: str
    procure_quantity: int
    allotment_available: int
    min_order_qty: int
    unit_cost_inr: float
    suggested_sell_price_inr: float
    total_investment_inr: float
    expected_profit_inr: float
    sell_through_probability: float
    max_downside_loss_inr: float
    buy_timing_recommendation: str
    release_cutoff_days: int
    opportunity_score: Optional[float] = None
    reason_string: Optional[str] = None


class OptimizationRunResponse(BaseModel):
    """Complete summary of an optimization run."""

    run_id: str
    idempotency_key: Optional[str] = None
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    created_by_user_id: str
    budget_inr: float
    risk_appetite: str
    total_capital_committed_inr: Optional[float] = None
    budget_utilization_pct: Optional[float] = None
    expected_profit_inr: Optional[float] = None
    expected_roi_pct: Optional[float] = None
    profit_p10_inr: Optional[float] = None
    profit_p50_inr: Optional[float] = None
    profit_p90_inr: Optional[float] = None
    cvar_alpha_loss_inr: Optional[float] = None
    worst_case_loss_inr: Optional[float] = None
    shadow_price_budget_inr: Optional[float] = None
    num_items_procured: Optional[int] = None
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    approver_user_id: Optional[str] = None
    approver_notes: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None


class ApprovalActionRequest(BaseModel):
    """Financial approval or rejection payload."""

    approved: bool = Field(..., description="True to approve purchase commitments, False to reject")
    notes: Optional[str] = Field(default=None, description="Mandatory notes if rejecting")


class StressTestRequest(BaseModel):
    """Payload to trigger a what-if stress simulation on an existing run."""

    run_id: Optional[str] = None
    demand_shock_pct: float = Field(default=-20.0, ge=-80.0, le=50.0, description="E.g. -20 for -20% demand")
    cost_inflation_pct: float = Field(default=10.0, ge=-20.0, le=50.0, description="E.g. +10 for +10% cost")
    cancellation_surge_pct: float = Field(default=50.0, ge=0.0, le=200.0, description="E.g. +50 for +50% cancellations")
