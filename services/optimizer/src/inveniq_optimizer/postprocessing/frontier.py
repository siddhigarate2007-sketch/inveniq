"""Efficient Frontier analysis for risk-return trade-offs."""

from typing import Any
import numpy as np
import pandas as pd
import structlog
from inveniq_optimizer.engine.solver import StochasticOptimizer

logger = structlog.get_logger(__name__)


class EfficientFrontierEngine:
    """Computes the Pareto-optimal frontier of Expected Profit vs Conditional Value-at-Risk."""

    def __init__(self, optimizer: StochasticOptimizer) -> None:
        self.optimizer = optimizer

    def compute_frontier(
        self,
        candidates: pd.DataFrame,
        num_points: int = 5,
    ) -> list[dict[str, Any]]:
        """Sweeps risk aversion lambda from 0.05 (aggressive) to 1.80 (conservative)."""
        logger.info("Computing efficient frontier curve", points=num_points)

        lambda_sweep = np.linspace(0.05, 1.80, num_points)
        frontier_points = []

        # Fix scenarios so comparison across lambda is strictly deterministic
        raw_D, raw_probs = self.optimizer.scenario_gen.generate_scenarios(candidates, num_scenarios=300)
        D_scenarios, probs = self.optimizer.scenario_reducer.reduce(raw_D, raw_probs)
        fixed_scenarios = (D_scenarios, probs)

        for lam in lambda_sweep:
            self.optimizer.risk_lambda = float(lam)
            sol = self.optimizer.optimize(candidates, custom_scenarios=fixed_scenarios)
            frontier_points.append({
                "risk_lambda": round(float(lam), 2),
                "expected_profit_inr": sol["expected_profit_inr"],
                "cvar_loss_inr": sol["cvar_alpha_loss_inr"],
                "worst_loss_inr": sol["worst_case_loss_inr"],
                "total_invested_inr": sol["total_capital_committed_inr"],
                "expected_roi_pct": sol["expected_roi_pct"],
                "items_procured": sol["num_items_procured"],
            })

        logger.info("Efficient frontier computation complete", points_evaluated=len(frontier_points))
        return frontier_points
