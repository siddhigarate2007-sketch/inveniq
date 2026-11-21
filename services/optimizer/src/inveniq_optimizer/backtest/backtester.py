"""Walk-Forward Backtesting and Macro Stress Testing Engine for InvenIQ."""

from typing import Any
import numpy as np
import pandas as pd
import structlog
from inveniq_optimizer.backtest.baselines import BaselineStrategies
from inveniq_optimizer.engine.solver import StochasticOptimizer

logger = structlog.get_logger(__name__)


class WalkForwardBacktester:
    """Simulates out-of-time financial realization against baseline procurement strategies."""

    def __init__(self, optimizer: StochasticOptimizer) -> None:
        self.optimizer = optimizer

    @staticmethod
    def simulate_realization(
        procured_q: np.ndarray,
        realized_demand: np.ndarray,
        cost_price: np.ndarray,
        sell_price: np.ndarray,
        salvage_rate: float = 0.20,
    ) -> dict[str, float]:
        """Simulates sales, unsold inventory salvage, and realized net profit."""
        sold_qty = np.minimum(procured_q, realized_demand)
        unsold_qty = np.maximum(0, procured_q - sold_qty)

        salvage_price = cost_price * salvage_rate
        revenue = float(np.sum(sell_price * sold_qty))
        salvage = float(np.sum(salvage_price * unsold_qty))
        cost = float(np.sum(cost_price * procured_q))
        profit = revenue + salvage - cost

        total_procured = int(np.sum(procured_q))
        total_sold = int(np.sum(sold_qty))
        sell_through = (total_sold / max(1, total_procured)) * 100.0
        unsold_loss = float(np.sum((cost_price - salvage_price) * unsold_qty))
        roi = (profit / max(1.0, cost)) * 100.0

        return {
            "procured_units": total_procured,
            "sold_units": total_sold,
            "capital_invested_inr": round(cost, 2),
            "realized_revenue_inr": round(revenue, 2),
            "salvage_recovered_inr": round(salvage, 2),
            "unsold_inventory_loss_inr": round(unsold_loss, 2),
            "realized_profit_inr": round(profit, 2),
            "realized_roi_pct": round(roi, 2),
            "sell_through_pct": round(sell_through, 2),
        }

    def run_backtest(
        self,
        candidates: pd.DataFrame,
        actual_demands: np.ndarray,
    ) -> dict[str, Any]:
        """Runs comparative walk-forward backtest across InvenIQ and 4 baseline heuristics."""
        logger.info("Executing walk-forward strategy backtest")
        budget = self.optimizer.budget_inr
        c = candidates["cost_price_inr"].to_numpy()
        p = candidates["sell_price_inr"].to_numpy()

        # 1. InvenIQ Stochastic MILP Solution
        sol = self.optimizer.optimize(candidates)
        q_inveniq = np.zeros(len(candidates), dtype=int)
        for rec in sol["recommendations"]:
            idx = candidates[candidates["entity_id"] == rec["item_id"]].index
            if len(idx) > 0:
                q_inveniq[idx[0]] = rec["procure_quantity"]

        # 2. Baseline Procurement Quantities
        q_last_year = BaselineStrategies.buy_last_year_volumes(candidates, budget)
        q_prop_demand = BaselineStrategies.proportional_to_demand(candidates, budget)
        q_top_margin = BaselineStrategies.top_margin_first_greedy(candidates, budget)
        q_random = BaselineStrategies.random_allocation(candidates, budget)

        # 3. Simulate Realized Financial Outcomes
        res_inveniq = self.simulate_realization(q_inveniq, actual_demands, c, p)
        res_last_year = self.simulate_realization(q_last_year, actual_demands, c, p)
        res_prop_demand = self.simulate_realization(q_prop_demand, actual_demands, c, p)
        res_top_margin = self.simulate_realization(q_top_margin, actual_demands, c, p)
        res_random = self.simulate_realization(q_random, actual_demands, c, p)

        # 4. Uplift Calculations
        profit_inveniq = res_inveniq["realized_profit_inr"]
        profit_last_year = res_last_year["realized_profit_inr"]
        uplift_vs_last_year = profit_inveniq - profit_last_year
        uplift_pct = (uplift_vs_last_year / max(1.0, abs(profit_last_year))) * 100.0

        # Unsold loss reduction
        loss_inveniq = res_inveniq["unsold_inventory_loss_inr"]
        loss_last_year = res_last_year["unsold_inventory_loss_inr"]
        waste_reduction_pct = ((loss_last_year - loss_inveniq) / max(1.0, loss_last_year)) * 100.0

        comparison_table = [
            {"strategy": "InvenIQ (Stochastic MILP + CVaR)", **res_inveniq},
            {"strategy": "Baseline 1: Last Year Volumes", **res_last_year},
            {"strategy": "Baseline 2: Proportional to Demand", **res_prop_demand},
            {"strategy": "Baseline 3: Top Margin First", **res_top_margin},
            {"strategy": "Baseline 4: Random Allocation", **res_random},
        ]

        report = {
            "status": "SUCCESS",
            "budget_inr": budget,
            "strategies_evaluated": comparison_table,
            "quantified_business_impact": {
                "profit_uplift_inr": round(uplift_vs_last_year, 2),
                "profit_uplift_pct": round(uplift_pct, 2),
                "unsold_waste_reduction_pct": round(waste_reduction_pct, 2),
                "inveniq_sell_through_pct": res_inveniq["sell_through_pct"],
                "baseline_sell_through_pct": res_last_year["sell_through_pct"],
            },
        }

        logger.info(
            "Backtest completed successfully",
            profit_uplift_inr=report["quantified_business_impact"]["profit_uplift_inr"],
            uplift_pct=report["quantified_business_impact"]["profit_uplift_pct"],
        )
        return report


class StressTestEngine:
    """Stress tests the inventory portfolio under severe macroeconomic shocks."""

    def __init__(self, optimizer: StochasticOptimizer) -> None:
        self.optimizer = optimizer

    def run_stress_tests(
        self,
        candidates: pd.DataFrame,
        base_realized_demands: np.ndarray,
    ) -> list[dict[str, Any]]:
        """Simulates 5 distinct macro stress events on the optimal inventory commitments."""
        logger.info("Executing portfolio macro stress tests")
        c = candidates["cost_price_inr"].to_numpy()
        p = candidates["sell_price_inr"].to_numpy()

        # Solve optimal portfolio under baseline conditions
        sol = self.optimizer.optimize(candidates)
        q_opt = np.zeros(len(candidates), dtype=int)
        for rec in sol["recommendations"]:
            idx = candidates[candidates["entity_id"] == rec["item_id"]].index
            if len(idx) > 0:
                q_opt[idx[0]] = rec["procure_quantity"]

        scenarios = [
            ("Nominal (Baseline Market)", base_realized_demands, c),
            ("Severe Demand Shock (-20% Demand)", base_realized_demands * 0.80, c),
            ("Supplier Inflation Shock (+10% Cost)", base_realized_demands, c * 1.10),
            ("Cancellation Surge (+50% Cancellations)", base_realized_demands * 0.85, c),
            ("Top Destination Collapse (Goa / Dubai Outage)", base_realized_demands.copy(), c),
        ]

        # Apply destination outage for scenario 5
        scenarios[4][1][0 : len(candidates) // 4] = 0.0

        stress_results = []
        for name, d_stress, c_stress in scenarios:
            res = WalkForwardBacktester.simulate_realization(q_opt, d_stress, c_stress, p)
            stress_results.append({
                "scenario_name": name,
                "realized_profit_inr": res["realized_profit_inr"],
                "realized_roi_pct": res["realized_roi_pct"],
                "sell_through_pct": res["sell_through_pct"],
                "unsold_inventory_loss_inr": res["unsold_inventory_loss_inr"],
                "capital_invested_inr": res["capital_invested_inr"],
            })

        logger.info("Stress testing complete", scenarios_evaluated=len(stress_results))
        return stress_results
