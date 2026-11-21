"""Evaluation metrics and rolling-origin cross-validation for demand models."""

from typing import Any
import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


class ForecastEvaluator:
    """Evaluates point and probabilistic forecasts with industry-standard travel metrics."""

    @staticmethod
    def wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Weighted Mean Absolute Percentage Error: sum(|y - y_hat|) / sum(y)."""
        denom = float(np.sum(y_true))
        if denom == 0.0:
            return 0.0
        return float(np.sum(np.abs(y_true - y_pred)) / denom)

    @staticmethod
    def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Symmetric Mean Absolute Percentage Error."""
        denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
        diff = np.abs(y_true - y_pred)
        mask = denom > 1e-6
        if not np.any(mask):
            return 0.0
        return float(np.mean(diff[mask] / denom[mask]) * 100.0)

    @staticmethod
    def pinball_loss(y_true: np.ndarray, q_pred: np.ndarray, tau: float) -> float:
        """Quantile pinball loss: mean(max(tau * (y - q), (1 - tau) * (q - y)))."""
        diff = y_true - q_pred
        return float(np.mean(np.maximum(tau * diff, (1.0 - tau) * -diff)))

    @staticmethod
    def interval_coverage(y_true: np.ndarray, q_low: np.ndarray, q_high: np.ndarray) -> float:
        """Prediction Interval Coverage Probability (PICP)."""
        covered = (y_true >= q_low) & (y_true <= q_high)
        return float(np.mean(covered))

    @staticmethod
    def mean_interval_width(q_low: np.ndarray, q_high: np.ndarray) -> float:
        """Mean Prediction Interval Width (MPIW)."""
        return float(np.mean(q_high - q_low))

    @staticmethod
    def forecast_bias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Forecast Bias: sum(y_hat - y) / sum(y)."""
        denom = float(np.sum(y_true))
        if denom == 0.0:
            return 0.0
        return float(np.sum(y_pred - y_true) / denom)

    def evaluate_all(
        self,
        y_true: np.ndarray,
        q10: np.ndarray,
        q50: np.ndarray,
        q90: np.ndarray,
    ) -> dict[str, float]:
        """Calculates full metrics dictionary."""
        return {
            "wmape": round(self.wmape(y_true, q50), 4),
            "smape": round(self.smape(y_true, q50), 2),
            "bias": round(self.forecast_bias(y_true, q50), 4),
            "pinball_10": round(self.pinball_loss(y_true, q10, 0.10), 4),
            "pinball_50": round(self.pinball_loss(y_true, q50, 0.50), 4),
            "pinball_90": round(self.pinball_loss(y_true, q90, 0.90), 4),
            "coverage_80": round(self.interval_coverage(y_true, q10, q90), 4),
            "mean_interval_width": round(self.mean_interval_width(q10, q90), 2),
        }

    def evaluate_by_segments(
        self,
        df_results: pd.DataFrame,
        segment_cols: list[str],
        y_col: str = "uncensored_demand",
        q10_col: str = "q_10",
        q50_col: str = "q_50",
        q90_col: str = "q_90",
    ) -> pd.DataFrame:
        """Computes metrics broken down across market segments."""
        rows = []
        for grp_keys, grp in df_results.groupby(segment_cols):
            if not isinstance(grp_keys, tuple):
                grp_keys = (grp_keys,)
            y_t = grp[y_col].to_numpy()
            q1 = grp[q10_col].to_numpy()
            q5 = grp[q50_col].to_numpy()
            q9 = grp[q90_col].to_numpy()

            metrics = self.evaluate_all(y_t, q1, q5, q9)
            row_dict = {col: grp_keys[i] for i, col in enumerate(segment_cols)}
            row_dict["sample_count"] = len(grp)
            row_dict.update(metrics)
            rows.append(row_dict)

        return pd.DataFrame(rows)
