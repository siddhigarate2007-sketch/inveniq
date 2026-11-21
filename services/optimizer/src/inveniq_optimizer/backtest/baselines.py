"""Benchmark heuristic procurement strategies for backtest comparison."""

import numpy as np
import pandas as pd


class BaselineStrategies:
    """Implements industry benchmark procurement heuristics."""

    @staticmethod
    def buy_last_year_volumes(
        candidates: pd.DataFrame,
        budget: float,
    ) -> np.ndarray:
        """Buys last year's historical sales quantities, scaled to fit within budget."""
        # Use lag_365 or observed baseline as proxy for last year volume
        last_year_qty = candidates.get("lag_365", candidates["allotment_size"] * 0.5).to_numpy()
        costs = candidates["cost_price_inr"].to_numpy()

        # Scale down if exceeds budget
        total_cost = np.sum(last_year_qty * costs)
        scale = min(1.0, budget / max(1.0, total_cost))
        procured = np.floor(last_year_qty * scale).astype(int)
        allotment = candidates["allotment_size"].to_numpy()
        return np.clip(procured, 0, allotment)

    @staticmethod
    def proportional_to_demand(
        candidates: pd.DataFrame,
        budget: float,
    ) -> np.ndarray:
        """Allocates budget in direct proportion to forecast median demand."""
        demands = candidates.get("q_50", np.ones(len(candidates))).to_numpy()
        costs = candidates["cost_price_inr"].to_numpy()
        allotment = candidates["allotment_size"].to_numpy()

        demand_weights = demands / np.sum(demands)
        capital_per_item = demand_weights * budget
        procured = np.floor(capital_per_item / costs).astype(int)
        return np.clip(procured, 0, allotment)

    @staticmethod
    def top_margin_first_greedy(
        candidates: pd.DataFrame,
        budget: float,
    ) -> np.ndarray:
        """Greedily buys maximum allotment of highest unit gross margin items until budget is exhausted."""
        costs = candidates["cost_price_inr"].to_numpy()
        sells = candidates["sell_price_inr"].to_numpy()
        margins = (sells - costs) / np.maximum(1.0, sells)
        allotment = candidates["allotment_size"].to_numpy()

        sorted_indices = np.argsort(-margins)
        procured = np.zeros(len(candidates), dtype=int)
        remaining_budget = budget

        for idx in sorted_indices:
            c = costs[idx]
            max_buy = int(allotment[idx])
            affordable = int(remaining_budget // c)
            buy_qty = min(max_buy, affordable)
            if buy_qty > 0:
                procured[idx] = buy_qty
                remaining_budget -= buy_qty * c
            if remaining_budget < np.min(costs):
                break

        return procured

    @staticmethod
    def random_allocation(
        candidates: pd.DataFrame,
        budget: float,
        seed: int = 42,
    ) -> np.ndarray:
        """Randomly selects inventory items respecting budget constraint."""
        rng = np.random.default_rng(seed)
        allotment = candidates["allotment_size"].to_numpy()
        costs = candidates["cost_price_inr"].to_numpy()

        procured = np.zeros(len(candidates), dtype=int)
        remaining = budget
        indices = rng.permutation(len(candidates))

        for idx in indices:
            max_buy = int(allotment[idx])
            c = costs[idx]
            affordable = int(remaining // c)
            if affordable > 0:
                buy = rng.integers(1, min(max_buy, affordable) + 1)
                procured[idx] = buy
                remaining -= buy * c
            if remaining < np.min(costs):
                break

        return procured
