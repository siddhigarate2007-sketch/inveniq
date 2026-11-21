"""Hierarchical Global Quantile LightGBM Forecaster for InvenIQ."""

from typing import Any
import lightgbm as lgb
import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


class QuantileLightGBMForecaster:
    """Trains probabilistic quantile regressors (P10, P50, P90) with pinball loss."""

    def __init__(
        self,
        quantiles: list[float] | None = None,
        num_boost_round: int = 120,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        min_child_samples: int = 20,
    ) -> None:
        self.quantiles = quantiles or [0.10, 0.50, 0.90]
        self.num_boost_round = num_boost_round
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.models: dict[float, lgb.Booster] = {}
        self.feature_names: list[str] = []

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series | np.ndarray,
        feature_names: list[str] | None = None,
    ) -> "QuantileLightGBMForecaster":
        """Fits individual quantile models for each target percentile."""
        self.feature_names = feature_names or list(X_train.columns)
        X_mat = X_train[self.feature_names].copy()
        y_vec = np.array(y_train, dtype=float)

        # Categorical columns
        cat_features = [
            c for c in self.feature_names
            if X_mat[c].dtype.name == "category" or X_mat[c].dtype == "object"
        ]
        for c in cat_features:
            X_mat[c] = X_mat[c].astype("category")

        dtrain = lgb.Dataset(X_mat, label=y_vec, free_raw_data=False)

        for q in self.quantiles:
            logger.info("Training LightGBM quantile model", quantile=q, trees=self.num_boost_round)
            params: dict[str, Any] = {
                "objective": "quantile",
                "alpha": q,
                "learning_rate": self.learning_rate,
                "num_leaves": self.num_leaves,
                "min_child_samples": self.min_child_samples,
                "verbosity": -1,
                "feature_pre_filter": False,
                "force_col_wise": True,
            }
            booster = lgb.train(
                params=params,
                train_set=dtrain,
                num_boost_round=self.num_boost_round,
            )
            self.models[q] = booster

        return self

    def predict_quantiles(self, X_test: pd.DataFrame) -> pd.DataFrame:
        """Generates calibrated, monotonically ordered P10, P50, and P90 predictions."""
        X_mat = X_test[self.feature_names].copy()
        cat_features = [
            c for c in self.feature_names
            if X_mat[c].dtype.name == "category" or X_mat[c].dtype == "object"
        ]
        for c in cat_features:
            X_mat[c] = X_mat[c].astype("category")

        raw_preds: dict[str, np.ndarray] = {}
        for q in self.quantiles:
            raw_preds[f"q_{int(q*100)}"] = np.maximum(0.0, self.models[q].predict(X_mat))

        df_preds = pd.DataFrame(raw_preds, index=X_test.index)

        # Enforce quantile monotonicity (q10 <= q50 <= q90)
        q10_col = "q_10" if "q_10" in df_preds.columns else f"q_{int(self.quantiles[0]*100)}"
        q50_col = "q_50" if "q_50" in df_preds.columns else f"q_{int(self.quantiles[1]*100)}"
        q90_col = "q_90" if "q_90" in df_preds.columns else f"q_{int(self.quantiles[2]*100)}"

        df_preds[q50_col] = np.maximum(df_preds[q50_col], df_preds[q10_col])
        df_preds[q90_col] = np.maximum(df_preds[q90_col], df_preds[q50_col])

        return df_preds

    def get_feature_importances(self) -> pd.DataFrame:
        """Returns feature importances across trained boosters."""
        if 0.50 in self.models:
            median_booster = self.models[0.50]
        else:
            median_booster = next(iter(self.models.values()))

        gains = median_booster.feature_importance(importance_type="gain")
        splits = median_booster.feature_importance(importance_type="split")

        df_imp = pd.DataFrame({
            "feature": self.feature_names,
            "gain": gains,
            "split": splits,
        }).sort_values(by="gain", ascending=False).reset_index(drop=True)

        return df_imp
