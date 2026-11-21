"""Model and Data Drift Monitoring Engine for InvenIQ."""

from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DriftReport:
    """Summary of statistical drift tests across critical features."""

    feature_name: str
    psi_score: float
    drift_detected: bool
    ks_statistic: float
    ks_p_value: float
    action_required: str


class DriftMonitor:
    """Calculates Population Stability Index (PSI) and Kolmogorov-Smirnov drift statistics."""

    def __init__(self, psi_threshold: float = 0.20, ks_alpha: float = 0.05):
        self.psi_threshold = psi_threshold
        self.ks_alpha = ks_alpha

    def calculate_psi(
        self,
        reference: np.ndarray,
        current: np.ndarray,
        num_buckets: int = 10,
    ) -> float:
        """Computes Population Stability Index (PSI) between reference and current distribution.

        PSI < 0.10: No significant shift.
        0.10 <= PSI <= 0.20: Moderate shift, monitor closely.
        PSI > 0.20: Significant distribution drift, trigger retraining.
        """
        ref_clean = reference[~np.isnan(reference)]
        cur_clean = current[~np.isnan(current)]

        if len(ref_clean) == 0 or len(cur_clean) == 0:
            return 0.0

        # Create quantile bins based on reference data
        percentiles = np.linspace(0, 100, num_buckets + 1)
        bins = np.percentile(ref_clean, percentiles)
        bins[0] = -np.inf
        bins[-1] = np.inf

        # Calculate counts per bin
        ref_counts = np.histogram(ref_clean, bins=bins)[0]
        cur_counts = np.histogram(cur_clean, bins=bins)[0]

        # Convert to relative proportions with Laplace smoothing
        ref_pct = (ref_counts + 1e-4) / (len(ref_clean) + 1e-4 * num_buckets)
        cur_pct = (cur_counts + 1e-4) / (len(cur_clean) + 1e-4 * num_buckets)

        # PSI formula: sum((Actual - Expected) * ln(Actual / Expected))
        psi = float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))
        return round(max(0.0, psi), 4)

    def evaluate_ks_test(
        self,
        reference: np.ndarray,
        current: np.ndarray,
    ) -> tuple[float, float]:
        """Calculates two-sample Kolmogorov-Smirnov statistic without external heavy dependencies."""
        ref_sorted = np.sort(reference[~np.isnan(reference)])
        cur_sorted = np.sort(current[~np.isnan(current)])

        n1 = len(ref_sorted)
        n2 = len(cur_sorted)
        if n1 == 0 or n2 == 0:
            return 0.0, 1.0

        all_vals = np.concatenate([ref_sorted, cur_sorted])
        cdf1 = np.searchsorted(ref_sorted, all_vals, side="right") / n1
        cdf2 = np.searchsorted(cur_sorted, all_vals, side="right") / n2

        ks_stat = float(np.max(np.abs(cdf1 - cdf2)))
        # Asymptotic p-value approximation for two-sample KS
        en = np.sqrt(n1 * n2 / (n1 + n2))
        lambda_val = (en + 0.12 + 0.11 / en) * ks_stat
        p_val = float(2.0 * np.exp(-2.0 * lambda_val * lambda_val))
        p_val = min(1.0, max(0.0, p_val))
        return round(ks_stat, 4), round(p_val, 4)

    def assess_feature_drift(
        self,
        reference_df: pd.DataFrame,
        current_df: pd.DataFrame,
        feature_columns: list[str],
    ) -> list[DriftReport]:
        """Assesses drift across specified feature columns and outputs actionable triggers."""
        reports: list[DriftReport] = []

        for col in feature_columns:
            if col not in reference_df.columns or col not in current_df.columns:
                continue

            ref_vals = reference_df[col].to_numpy(dtype=float)
            cur_vals = current_df[col].to_numpy(dtype=float)

            psi = self.calculate_psi(ref_vals, cur_vals)
            ks_stat, p_val = self.evaluate_ks_test(ref_vals, cur_vals)

            drift_detected = psi > self.psi_threshold or p_val < self.ks_alpha

            if psi > 0.20:
                action = "TRIGGER_RETRAINING: Significant distribution shift detected."
            elif psi >= 0.10:
                action = "MONITOR: Moderate feature shift observed."
            else:
                action = "HEALTHY: Stable distribution."

            report = DriftReport(
                feature_name=col,
                psi_score=psi,
                drift_detected=drift_detected,
                ks_statistic=ks_stat,
                ks_p_value=p_val,
                action_required=action,
            )
            reports.append(report)
            logger.info("Drift evaluation completed", feature=col, psi=psi, action=action)

        return reports
