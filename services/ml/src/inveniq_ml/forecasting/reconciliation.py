"""Hierarchical Forecast Reconciliation for InvenIQ.

Ensures mathematical coherence across travel aggregation levels:
Destination -> Product Type -> Entity (Hotel/Flight) -> Date
"""

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


class HierarchicalReconciler:
    """Reconciles multi-level travel demand forecasts to guarantee aggregate coherence."""

    @staticmethod
    def top_down_reconcile(
        df_entity_forecasts: pd.DataFrame,
        dest_totals: pd.DataFrame,
        date_col: str = "travel_date",
        dest_col: str = "destination_id",
        pred_col: str = "q_50",
    ) -> pd.DataFrame:
        """Reconciles bottom-up entity forecasts to match destination-level aggregate forecasts."""
        df = df_entity_forecasts.copy()

        # Compute bottom-up destination sums
        group_sums = (
            df.groupby([dest_col, date_col])[pred_col]
            .transform("sum")
            .replace(0, np.nan)
        )

        # Merge top-down destination target
        dest_target_map = dest_totals.set_index([dest_col, date_col])["target_demand"].to_dict()

        target_series = []
        for _, row in df.iterrows():
            key = (row[dest_col], row[date_col])
            target_series.append(dest_target_map.get(key, np.nan))

        df["dest_target"] = target_series

        # Proportional reconciliation factor: Target / BottomUpSum
        scaling_factor = df["dest_target"] / group_sums
        scaling_factor = scaling_factor.fillna(1.0)

        df[f"{pred_col}_reconciled"] = np.round(df[pred_col] * scaling_factor, 2)
        df[f"{pred_col}_reconciled"] = np.maximum(0.0, df[f"{pred_col}_reconciled"])

        logger.info(
            "Hierarchical top-down reconciliation completed",
            entities_reconciled=len(df),
            median_scaling_factor=round(float(scaling_factor.median()), 3),
        )
        return df

    @staticmethod
    def bottom_up_aggregate(
        df_entity_forecasts: pd.DataFrame,
        group_cols: list[str],
        pred_cols: list[str],
    ) -> pd.DataFrame:
        """Aggregates bottom-up entity predictions to destination or product levels."""
        agg_dict = {col: "sum" for col in pred_cols}
        df_agg = df_entity_forecasts.groupby(group_cols).agg(agg_dict).reset_index()
        return df_agg
