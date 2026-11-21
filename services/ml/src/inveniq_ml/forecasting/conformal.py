"""Conformalized Quantile Regression (CQR) for InvenIQ.

Guarantees valid finite-sample coverage for demand forecast prediction intervals.
"""

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


class ConformalQuantileCalibrator:
    """Calibrates P10-P90 prediction intervals using conformal non-conformity scores."""

    def __init__(self, desired_coverage: float = 0.80) -> None:
        self.desired_coverage = desired_coverage
        self.conformal_adjustment: float = 0.0
        self.is_calibrated: bool = False

    def calibrate(
        self,
        y_true: pd.Series | np.ndarray,
        q10_pred: pd.Series | np.ndarray,
        q90_pred: pd.Series | np.ndarray,
    ) -> float:
        """Computes conformal non-conformity score Q on calibration set."""
        y = np.array(y_true, dtype=float)
        low = np.array(q10_pred, dtype=float)
        high = np.array(q90_pred, dtype=float)

        n = len(y)
        if n == 0:
            raise ValueError("Calibration set cannot be empty.")

        # Non-conformity score: distance outside the predicted interval
        scores = np.maximum(low - y, y - high)

        # Conformal quantile level: ceil((n+1) * desired_coverage) / n
        level = min(1.0, np.ceil((n + 1) * self.desired_coverage) / n)
        self.conformal_adjustment = float(np.quantile(scores, level, method="higher"))
        self.is_calibrated = True

        logger.info(
            "Conformal calibration complete",
            sample_size=n,
            target_coverage=self.desired_coverage,
            adjustment_delta=round(self.conformal_adjustment, 3),
        )
        return self.conformal_adjustment

    def adjust_intervals(
        self,
        q10_pred: pd.Series | np.ndarray,
        q90_pred: pd.Series | np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Applies conformal adjustment to raw quantile predictions."""
        if not self.is_calibrated:
            raise RuntimeError("Calibrator has not been fitted. Call calibrate() first.")

        low = np.array(q10_pred, dtype=float) - self.conformal_adjustment
        high = np.array(q90_pred, dtype=float) + self.conformal_adjustment

        # Enforce non-negativity and ordering
        calibrated_low = np.maximum(0.0, low)
        calibrated_high = np.maximum(calibrated_low, high)

        return calibrated_low, calibrated_high
