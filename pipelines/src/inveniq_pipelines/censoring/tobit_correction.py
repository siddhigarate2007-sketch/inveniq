"""Demand Un-censoring Engine for InvenIQ.

Implements:
1. Search Look-to-Book (L2B) multiplier uplift for capacity-exhausted periods.
2. Tobit-style Heckman / Inverse Mills Ratio correction for right-censored booking observations.
"""

from typing import Any
import numpy as np
import pandas as pd
from scipy.stats import norm
import structlog

logger = structlog.get_logger(__name__)


class DemandCensoringCorrection:
    """Corrects historical sales observations where capacity caps true latent demand."""

    @staticmethod
    def calculate_baseline_look_to_book(
        df_searches: pd.DataFrame,
        soldout_dates: set[tuple[str, Any]],
    ) -> dict[str, float]:
        """Calculates median look-to-book ratio on non-sold-out dates per destination/product."""
        df = df_searches.copy()
        df["entity_date_key"] = list(zip(df["entity_id"], df["travel_date"]))
        df_uncensored = df[~df["entity_date_key"].isin(soldout_dates)].copy()

        df_uncensored["l2b"] = (
            df_uncensored["bookings_count"] / df_uncensored["results_shown"].replace(0, np.nan)
        )
        # Fallback global median if specific entity group has insufficient history
        global_median = float(df_uncensored["l2b"].median())
        if np.isnan(global_median) or global_median <= 0:
            global_median = 0.035

        l2b_per_dest = (
            df_uncensored.groupby("destination_id")["l2b"]
            .median()
            .to_dict()
        )
        return {k: (v if not np.isnan(v) and v > 0 else global_median) for k, v in l2b_per_dest.items()}

    @staticmethod
    def inverse_mills_ratio_right_censored(c: float, mu: float, sigma: float) -> float:
        """Computes E[D | D >= c] for right-censored normal variable D ~ N(mu, sigma^2).

        E[D | D >= c] = mu + sigma * (phi((c - mu) / sigma) / (1 - Phi((c - mu) / sigma)))
        """
        if sigma <= 0:
            return max(c, mu)
        alpha = (c - mu) / sigma
        denom = 1.0 - norm.cdf(alpha)
        if denom < 1e-6:
            # Deep in the right tail, linear asymptotic approximation
            return c + sigma * 0.5
        imr = norm.pdf(alpha) / denom
        return float(mu + sigma * imr)

    def uncensor_demand(
        self,
        df_bookings: pd.DataFrame,
        df_searches: pd.DataFrame,
        df_soldouts: pd.DataFrame,
    ) -> pd.DataFrame:
        """Produces un-censored latent demand estimates combining L2B and Tobit corrections."""
        logger.info("Starting demand un-censoring process", bookings=len(df_bookings), soldouts=len(df_soldouts))

        # Build sold-out lookup set: (entity_id, travel_date) -> soldout details
        soldout_lookup: dict[tuple[str, Any], dict[str, Any]] = {}
        for _, row in df_soldouts.iterrows():
            key = (str(row["entity_id"]), row["travel_date"])
            soldout_lookup[key] = {
                "allotment": float(row["allotment_capacity"]),
                "lost_demand_est": float(row.get("estimated_lost_demand", 0.0)),
                "unmet_searches": int(row.get("unmet_searches", 0)),
            }

        soldout_keys = set(soldout_lookup.keys())
        baseline_l2b_map = self.calculate_baseline_look_to_book(df_searches, soldout_keys)

        # Index search queries by (entity_id, travel_date)
        searches_map: dict[tuple[str, Any], int] = {}
        for _, s in df_searches.iterrows():
            searches_map[(str(s["entity_id"]), s["travel_date"])] = int(s["results_shown"])

        # Aggregate observed bookings per (entity_id, destination_id, product_type, travel_date)
        daily_bookings = (
            df_bookings[~df_bookings["cancelled_flag"]]
            .groupby(["entity_id", "destination_id", "product_type", "travel_date"])
            .agg(observed_qty=("quantity", "sum"), avg_sell_price=("sell_price_inr", "mean"))
            .reset_index()
        )

        records = []
        for _, row in daily_bookings.iterrows():
            ent_id = str(row["entity_id"])
            dest_id = str(row["destination_id"])
            ptype = str(row["product_type"])
            t_date = row["travel_date"]
            obs_qty = float(row["observed_qty"])
            avg_price = float(row["avg_sell_price"])

            key = (ent_id, t_date)
            is_soldout = key in soldout_lookup
            searches_count = searches_map.get(key, 0)
            baseline_l2b = baseline_l2b_map.get(dest_id, 0.035)

            if is_soldout:
                sold_info = soldout_lookup[key]
                allotment = sold_info["allotment"]

                # 1. Look-to-book uplift estimate
                l2b_demand = float(searches_count * baseline_l2b)

                # 2. Tobit expected truncated value
                # Using local rolling mean and std
                mu_est = obs_qty * 1.15
                sigma_est = max(3.0, obs_qty * 0.25)
                tobit_demand = self.inverse_mills_ratio_right_censored(allotment, mu_est, sigma_est)

                # Final combined un-censored demand: max of observed, L2B, and Tobit
                uncensored_demand = round(max(obs_qty, l2b_demand, tobit_demand), 2)
                censored_flag = True
            else:
                allotment = obs_qty * 2.0  # Surplus capacity
                uncensored_demand = obs_qty
                censored_flag = False

            records.append({
                "entity_id": ent_id,
                "destination_id": dest_id,
                "product_type": ptype,
                "travel_date": t_date,
                "observed_bookings": obs_qty,
                "allotment_capacity": allotment,
                "is_censored": censored_flag,
                "searches_count": searches_count,
                "uncensored_demand": uncensored_demand,
                "demand_uplift": round(uncensored_demand - obs_qty, 2),
                "avg_sell_price_inr": avg_price,
            })

        df_result = pd.DataFrame(records)
        censored_count = df_result["is_censored"].sum()
        total_uplift = df_result["demand_uplift"].sum()

        logger.info(
            "Completed demand un-censoring",
            total_records=len(df_result),
            censored_records=int(censored_count),
            total_latent_demand_recovered=round(float(total_uplift), 1),
        )
        return df_result
