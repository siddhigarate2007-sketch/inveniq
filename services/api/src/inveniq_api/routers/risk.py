"""Risk analytics, efficient frontier, and what-if stress testing endpoints."""

from typing import Any
from fastapi import APIRouter, Depends, Query
from inveniq_api.auth.rbac import get_current_user
from inveniq_core.db_store import db_store
from inveniq_core.schemas.optimization import StressTestRequest
from inveniq_core.schemas.user import User
from inveniq_optimizer.backtest.backtester import StressTestEngine
from inveniq_optimizer.engine.solver import StochasticOptimizer
from inveniq_optimizer.postprocessing.frontier import EfficientFrontierEngine
from inveniq_optimizer.postprocessing.sensitivity import SensitivityEngine

router = APIRouter(prefix="/risk", tags=["Risk & Simulation"])


@router.get("/frontier")
async def get_efficient_frontier(
    budget_inr: float = Query(50_000_000.0, gt=0),
    points: int = Query(5, ge=3, le=10),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Calculates Pareto-optimal Efficient Frontier (Expected Profit vs CVaR Loss)."""
    candidates = db_store.load_candidates_for_optimization()
    optimizer = StochasticOptimizer(budget_inr=budget_inr, target_scenarios=20)
    engine = EfficientFrontierEngine(optimizer)
    return engine.compute_frontier(candidates, num_points=points)


@router.get("/sensitivity")
async def get_budget_sensitivity(
    budget_inr: float = Query(50_000_000.0, gt=0),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Evaluates marginal ROI and shadow prices across budget multipliers [0.7x - 1.3x]."""
    candidates = db_store.load_candidates_for_optimization()
    optimizer = StochasticOptimizer(budget_inr=budget_inr, target_scenarios=20)
    engine = SensitivityEngine(optimizer)
    return engine.compute_budget_sensitivity(candidates)


@router.post("/stress-test")
async def run_stress_test(
    payload: StressTestRequest,
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Simulates portfolio realization under demand collapse, cost inflation, and cancellation surges."""
    candidates = db_store.load_candidates_for_optimization()
    base_demands = candidates["q_50"].to_numpy()

    optimizer = StochasticOptimizer(budget_inr=50_000_000.0, target_scenarios=20)
    stress_engine = StressTestEngine(optimizer)
    return stress_engine.run_stress_tests(candidates, base_demands)
