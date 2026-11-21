"""Calibrated Cancellation & Timing Model for InvenIQ.

Implements:
1. Gradient boosting binary classification of booking cancellation risk
2. Platt / Isotonic probability calibration
3. Survival view: cancellation timing relative to supplier release cutoff dates
"""

from typing import Any
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
import structlog

logger = structlog.get_logger(__name__)


class CalibratedCancellationModel:
    """Predicts calibrated booking cancellation probability and timing risk."""

    def __init__(self, num_boost_round: int = 80, learning_rate: float = 0.05) -> None:
        self.num_boost_round = num_boost_round
        self.learning_rate = learning_rate
        self.booster: lgb.Booster | None = None
        self.calibrator: IsotonicRegression | None = None
        self.feature_names: list[str] = []
        self.is_fitted: bool = False

    def prepare_training_features(self, df_bookings: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str]]:
        """Prepares features and binary cancellation target from bookings fact table."""
        df = df_bookings.copy()

        # Target: binary cancellation flag
        y = df["cancelled_flag"].astype(int)

        feature_cols = [
            "lead_time_days", "quantity", "sell_price_inr", "cost_price_inr",
            "product_type", "destination_id", "supplier_id"
        ]
        available_cols = [c for c in feature_cols if c in df.columns]

        X = df[available_cols].copy()
        cat_cols = ["product_type", "destination_id", "supplier_id"]
        for c in cat_cols:
            if c in X.columns:
                X[c] = X[c].astype("category")

        return X, y, available_cols

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series | np.ndarray,
        X_cal: pd.DataFrame | None = None,
        y_cal: pd.Series | np.ndarray | None = None,
    ) -> "CalibratedCancellationModel":
        """Fits LightGBM classifier and applies isotonic probability calibration."""
        self.feature_names = list(X_train.columns)
        y_arr = np.array(y_train, dtype=int)

        cat_features = [
            c for c in self.feature_names
            if X_train[c].dtype.name == "category" or X_train[c].dtype == "object"
        ]

        logger.info("Training LightGBM cancellation classifier", samples=len(X_train))
        dtrain = lgb.Dataset(X_train, label=y_arr, free_raw_data=False)

        params: dict[str, Any] = {
            "objective": "binary",
            "metric": "binary_logloss",
            "learning_rate": self.learning_rate,
            "num_leaves": 31,
            "min_child_samples": 20,
            "verbosity": -1,
            "force_col_wise": True,
        }

        self.booster = lgb.train(
            params=params,
            train_set=dtrain,
            num_boost_round=self.num_boost_round,
        )

        # Isotonic probability calibration
        if X_cal is not None and y_cal is not None:
            raw_cal_probs = self.booster.predict(X_cal)
            y_cal_arr = np.array(y_cal, dtype=float)
        else:
            raw_cal_probs = self.booster.predict(X_train)
            y_cal_arr = y_arr.astype(float)

        self.calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.01, y_max=0.99)
        self.calibrator.fit(raw_cal_probs, y_cal_arr)
        self.is_fitted = True

        logger.info("Cancellation model calibrated successfully")
        return self

    def predict_probability(self, X: pd.DataFrame) -> np.ndarray:
        """Outputs calibrated cancellation probability P(Cancel=1)."""
        if not self.is_fitted or self.booster is None:
            raise RuntimeError("Model is not fitted.")

        X_mat = X[self.feature_names].copy()
        cat_features = [
            c for c in self.feature_names
            if X_mat[c].dtype.name == "category" or X_mat[c].dtype == "object"
        ]
        for c in cat_features:
            X_mat[c] = X_mat[c].astype("category")

        raw_probs = self.booster.predict(X_mat)
        if self.calibrator is not None:
            calibrated_probs = self.calibrator.predict(raw_probs)
        else:
            calibrated_probs = raw_probs

        return np.clip(calibrated_probs, 0.01, 0.99)

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series | np.ndarray) -> dict[str, float]:
        """Evaluates discrimination (AUC) and calibration (Brier score)."""
        y_true = np.array(y_test, dtype=int)
        y_prob = self.predict_probability(X_test)

        auc = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.5
        brier = float(brier_score_loss(y_true, y_prob))

        # Expected Calibration Error (ECE) with 10 bins
        bins = np.linspace(0, 1, 11)
        bin_indices = np.digitize(y_prob, bins) - 1
        ece = 0.0
        for b in range(10):
            mask = bin_indices == b
            if np.sum(mask) > 0:
                bin_acc = float(np.mean(y_true[mask]))
                bin_conf = float(np.mean(y_prob[mask]))
                ece += (np.sum(mask) / len(y_true)) * abs(bin_acc - bin_conf)

        metrics = {
            "roc_auc": round(auc, 4),
            "brier_score": round(brier, 4),
            "expected_calibration_error": round(ece, 4),
        }
        logger.info("Cancellation model evaluation metrics", **metrics)
        return metrics

    @staticmethod
    def estimate_timing_relative_to_cutoff(
        cancel_prob: float,
        lead_time_days: int,
        release_cutoff_days: int,
    ) -> dict[str, float]:
        """Survival estimation: splits cancellation risk into pre-cutoff vs post-cutoff."""
        if lead_time_days <= release_cutoff_days:
            # Booked inside cutoff: all cancellations incur penalty
            p_post_cutoff = cancel_prob
            p_pre_cutoff = 0.0
        else:
            # Booked prior to cutoff: cancellations typically occur mid-lead-time
            # P(cancel past cutoff) increases as lead_time approaches cutoff
            pre_cutoff_window = lead_time_days - release_cutoff_days
            pre_cutoff_share = min(0.85, max(0.20, pre_cutoff_window / float(lead_time_days)))
            p_pre_cutoff = cancel_prob * pre_cutoff_share
            p_post_cutoff = cancel_prob * (1.0 - pre_cutoff_share)

        return {
            "total_cancel_prob": round(cancel_prob, 4),
            "p_cancel_before_cutoff": round(p_pre_cutoff, 4),
            "p_cancel_after_cutoff": round(p_post_cutoff, 4),
        }
