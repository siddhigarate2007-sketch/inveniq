"""Benchmark baseline forecasting models for demand comparison."""

import numpy as np
import pandas as pd


class SeasonalNaiveForecaster:
    """Predicts future demand using the seasonal lag (default: 7-day day-of-week lag)."""

    def __init__(self, lag: int = 7) -> None:
        self.lag = lag
        self.history: dict[str, list[float]] = {}

    def fit(self, df_train: pd.DataFrame, target_col: str = "uncensored_demand") -> "SeasonalNaiveForecaster":
        for entity_id, grp in df_train.groupby("entity_id"):
            self.history[str(entity_id)] = grp[target_col].tolist()
        return self

    def predict(self, df_test: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in df_test.iterrows():
            ent = str(row["entity_id"])
            hist = self.history.get(ent, [])
            if len(hist) >= self.lag:
                pred = hist[-self.lag]
            elif len(hist) > 0:
                pred = float(np.mean(hist))
            else:
                pred = 10.0
            preds.append(max(0.0, float(pred)))
        return np.array(preds)


class RollingMeanForecaster:
    """Predicts future demand using an exponentially weighted or simple rolling average."""

    def __init__(self, window: int = 14) -> None:
        self.window = window
        self.history: dict[str, float] = {}

    def fit(self, df_train: pd.DataFrame, target_col: str = "uncensored_demand") -> "RollingMeanForecaster":
        for entity_id, grp in df_train.groupby("entity_id"):
            recent = grp[target_col].tail(self.window).tolist()
            self.history[str(entity_id)] = float(np.mean(recent)) if recent else 10.0
        return self

    def predict(self, df_test: pd.DataFrame) -> np.ndarray:
        preds = [max(0.0, self.history.get(str(row["entity_id"]), 10.0)) for _, row in df_test.iterrows()]
        return np.array(preds)
