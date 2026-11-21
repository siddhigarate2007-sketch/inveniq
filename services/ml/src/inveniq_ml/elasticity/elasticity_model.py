"""Econometric Price Elasticity Engine for InvenIQ.

Implements:
1. Double Machine Learning (DML) / Two-Stage Partialling Out to handle price endogeneity:
   Stage 1: Partial out calendar, seasonality, destination tier from ln(Price) and ln(Demand).
   Stage 2: Estimate segment-wise elasticity coefficients on orthogonalized residuals.
2. Demand-vs-Price curve generator D(p) = D_0 * (p / p_0)^epsilon for the stochastic optimizer.
"""

from typing import Any, Callable
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import structlog

logger = structlog.get_logger(__name__)


class PriceElasticityEngine:
    """Estimates causal price elasticity per market segment and generates demand curves."""

    def __init__(self, segments: list[str] | None = None) -> None:
        self.segments = segments or ["Luxury", "Midscale", "Budget"]
        self.elasticities: dict[str, float] = {
            "Luxury": -0.85,
            "Midscale": -1.45,
            "Budget": -2.15,
        }
        self.stage1_price_model: Ridge | None = None
        self.stage1_demand_model: Ridge | None = None
        self.is_fitted: bool = False

    def fit_double_ml(
        self,
        df: pd.DataFrame,
        price_col: str = "avg_sell_price_inr",
        demand_col: str = "uncensored_demand",
        segment_col: str = "segment",
        control_cols: list[str] | None = None,
    ) -> dict[str, float]:
        """Fits Two-Stage Double ML to resolve endogeneity and estimate segment elasticities."""
        logger.info("Fitting Double ML price elasticity estimator", total_samples=len(df))

        # Filter positive prices and demands
        valid_mask = (df[price_col] > 0) & (df[demand_col] > 0)
        df_valid = df[valid_mask].copy()

        log_p = np.log(df_valid[price_col].to_numpy())
        log_d = np.log(df_valid[demand_col].to_numpy())

        # Select control features (seasonality, day-of-week, festival, destination tier)
        if not control_cols:
            control_cols = [
                c for c in [
                    "sin_doy", "cos_doy", "sin_dow", "cos_dow", "is_weekend",
                    "is_festival", "is_holiday", "is_long_weekend", "dest_tier",
                    "avg_temp_celsius", "competitor_price_index"
                ] if c in df_valid.columns
            ]

        if not control_cols:
            # Fallback controls if specific columns missing
            W = np.ones((len(df_valid), 1))
        else:
            W = df_valid[control_cols].fillna(0).to_numpy()

        # Stage 1: Orthogonalize price and demand against exogenous controls
        self.stage1_price_model = Ridge(alpha=1.0)
        self.stage1_demand_model = Ridge(alpha=1.0)

        self.stage1_price_model.fit(W, log_p)
        self.stage1_demand_model.fit(W, log_d)

        # Residuals (orthogonalized variations)
        res_price = log_p - self.stage1_price_model.predict(W)
        res_demand = log_d - self.stage1_demand_model.predict(W)

        df_valid["res_price"] = res_price
        df_valid["res_demand"] = res_demand

        # Stage 2: Segment-wise OLS on residuals
        estimated_elasticities = {}
        for seg in self.segments:
            seg_data = df_valid[df_valid[segment_col] == seg]
            if len(seg_data) >= 10:
                p_var = np.var(seg_data["res_price"])
                if p_var > 1e-5:
                    # beta = cov(res_p, res_d) / var(res_p)
                    cov_pd = np.cov(seg_data["res_price"], seg_data["res_demand"])[0, 1]
                    beta = float(cov_pd / p_var)
                    # Enforce realistic economic bounds [-4.0, -0.2]
                    beta = max(-4.0, min(-0.2, beta))
                    estimated_elasticities[seg] = round(beta, 3)
                else:
                    estimated_elasticities[seg] = self.elasticities.get(seg, -1.45)
            else:
                estimated_elasticities[seg] = self.elasticities.get(seg, -1.45)

        self.elasticities.update(estimated_elasticities)
        self.is_fitted = True
        logger.info("Estimated causal price elasticities", elasticities=self.elasticities)
        return self.elasticities

    def get_demand_curve(
        self,
        base_price: float,
        base_demand: float,
        segment: str = "Midscale",
    ) -> Callable[[float], float]:
        """Returns demand function D(p) = base_demand * (p / base_price)^epsilon."""
        epsilon = self.elasticities.get(segment, -1.45)

        def demand_fn(p: float) -> float:
            if p <= 0 or base_price <= 0:
                return 0.0
            price_ratio = p / base_price
            demand_multiplier = float(price_ratio ** epsilon)
            return max(0.0, float(base_demand * demand_multiplier))

        return demand_fn

    def compute_optimal_unconstrained_price(
        self,
        cost_price: float,
        segment: str = "Midscale",
    ) -> float:
        """Computes microeconomic monopoly markup price under constant elasticity:

        p* = cost * (epsilon / (1 + epsilon)) for epsilon < -1.
        """
        eps = self.elasticities.get(segment, -1.45)
        if eps >= -1.0:
            # Inelastic demand: standard 35% margin markup guardrail
            return round(cost_price * 1.35, 2)
        optimal_markup = eps / (1.0 + eps)
        return round(float(cost_price * optimal_markup), 2)
