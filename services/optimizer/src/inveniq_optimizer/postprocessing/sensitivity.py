"""Budget sensitivity and shadow price analysis for InvenIQ."""

from typing import Any
import numpy as np
import pandas as pd
import structlog
from inveniq_optimizer.engine.solver import StochasticOptimizer

logger = structlog.get_logger(__name__)


class SensitivityEngine:
    """Evaluates marginal budget return curve and constraint bottlenecks."""

    def __init__(self, optimizer: StochasticOptimizer) -> None:
        self.optimizer = optimizer

    def compute_budget_sensitivity(
        self,
        candidates: pd.DataFrame,
        multipliers: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        """Sweeps budget from 0.70x to 1.30x base budget to compute marginal ROI."""
        mults = multipliers or [0.70, 0.85, 1.00, 1.15, 1.30]
        base_budget = self.optimizer.budget_inr

        raw_D, raw_probs = self.optimizer.scenario_gen.generate_scenarios(candidates, num_scenarios=250)
        D_scenarios, probs = self.optimizer.scenario_reducer.reduce(raw_D, raw_probs)
        fixed_scenarios = (D_scenarios, probs)

        results = []
        for m in mults:
            self.optimizer.budget_inr = base_budget * m
            sol = self.optimizer.optimize(candidates, custom_scenarios=fixed_scenarios)
            results.append({
                "budget_multiplier": round(m, 2),
                "budget_inr": round(self.optimizer.budget_inr, 2),
                "capital_invested_inr": sol["total_capital_committed_inr"],
                "expected_profit_inr": sol["expected_profit_inr"],
                "expected_roi_pct": sol["expected_roi_pct"],
                "cvar_loss_inr": sol["cvar_alpha_loss_inr"],
                "shadow_price_budget": sol["shadow_price_budget_inr"],
            })

        # Reset base budget
        self.optimizer.budget_inr = base_budget
        return results
