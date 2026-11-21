"""Monte Carlo scenario generation for travel inventory demand."""

from typing import Any
import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


class ScenarioGenerator:
    """Generates stochastic demand scenarios from calibrated forecast quantiles."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)

    def generate_scenarios(
        self,
        candidates: pd.DataFrame,
        num_scenarios: int = 1000,
        correlation_factor: float = 0.35,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generates Monte Carlo demand realization matrix D of shape (num_scenarios, num_items).

        Returns:
            D_scenarios: shape (num_scenarios, num_items) with realized un-censored effective demand
            probabilities: shape (num_scenarios,) uniform prior 1 / num_scenarios
        """
        num_items = len(candidates)
        if num_items == 0:
            raise ValueError("Candidates dataframe cannot be empty.")

        # Shared macro market shock Z ~ N(0, 1)
        z_macro = self.rng.normal(0, 1, size=(num_scenarios, 1))

        D_matrix = np.zeros((num_scenarios, num_items), dtype=float)

        for i, (_, row) in enumerate(candidates.iterrows()):
            p10 = float(row.get("q_10", 15.0))
            p50 = float(row.get("q_50", 30.0))
            p90 = float(row.get("q_90", 50.0))
            cancel_rate = float(row.get("cancel_prob", 0.08))

            # Estimate standard deviation from calibrated interval [P10, P90]
            sigma = max(1.0, (p90 - p10) / 2.563)
            mu = p50

            # Idiosyncratic component
            eps_item = self.rng.normal(0, 1, size=(num_scenarios, 1))

            # Correlated demand shock
            correlated_shock = np.sqrt(correlation_factor) * z_macro + np.sqrt(1.0 - correlation_factor) * eps_item
            raw_draws = mu + sigma * correlated_shock.flatten()

            # Net effective demand after cancellation
            effective_demand = np.maximum(0.0, raw_draws * (1.0 - cancel_rate))
            D_matrix[:, i] = np.round(effective_demand, 1)

        probabilities = np.ones(num_scenarios) / num_scenarios
        logger.info(
            "Generated Monte Carlo demand scenarios",
            items=num_items,
            scenarios=num_scenarios,
        )
        return D_matrix, probabilities
