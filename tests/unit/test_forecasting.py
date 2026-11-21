"""Unit tests for LightGBM quantile regression, conformal calibration, and reconciliation."""

import numpy as np
import pandas as pd
from inveniq_ml.forecasting.conformal import ConformalQuantileCalibrator
from inveniq_ml.forecasting.evaluation import ForecastEvaluator
from inveniq_ml.forecasting.lightgbm_model import QuantileLightGBMForecaster
from inveniq_ml.forecasting.reconciliation import HierarchicalReconciler


def test_quantile_lightgbm_monotonicity() -> None:
    np.random.seed(42)
    n = 200
    X = pd.DataFrame({
        "feat_1": np.random.randn(n),
        "feat_2": np.random.uniform(10, 50, n),
        "cat_1": pd.Categorical(np.random.choice(["A", "B", "C"], n)),
    })
    y = X["feat_2"] * 1.5 + np.random.normal(0, 5, n)

    forecaster = QuantileLightGBMForecaster(quantiles=[0.10, 0.50, 0.90], num_boost_round=15)
    forecaster.fit(X, y)

    preds = forecaster.predict_quantiles(X)
    assert "q_10" in preds.columns
    assert "q_50" in preds.columns
    assert "q_90" in preds.columns

    # Verify strict monotonicity: q_10 <= q_50 <= q_90 and non-negativity
    assert (preds["q_10"] <= preds["q_50"] + 1e-6).all()
    assert (preds["q_50"] <= preds["q_90"] + 1e-6).all()
    assert (preds["q_10"] >= 0.0).all()


def test_conformal_quantile_calibrator() -> None:
    calibrator = ConformalQuantileCalibrator(desired_coverage=0.80)

    y_true = np.array([10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0])
    q10 = y_true - 2.0  # slightly too narrow
    q90 = y_true + 2.0

    adj = calibrator.calibrate(y_true, q10, q90)
    assert calibrator.is_calibrated is True

    q10_adj, q90_adj = calibrator.adjust_intervals(q10, q90)
    assert len(q10_adj) == len(y_true)
    assert (q10_adj <= q90_adj).all()
    assert (q10_adj >= 0.0).all()


def test_hierarchical_top_down_reconciliation() -> None:
    df_entity = pd.DataFrame({
        "entity_id": ["E1", "E2", "E3", "E4"],
        "destination_id": ["D1", "D1", "D2", "D2"],
        "travel_date": ["2024-01-01", "2024-01-01", "2024-01-01", "2024-01-01"],
        "q_50": [40.0, 60.0, 30.0, 70.0],  # Bottom up: D1=100, D2=100
    })

    # Suppose top-down destination forecasts are D1=150, D2=80
    dest_totals = pd.DataFrame({
        "destination_id": ["D1", "D2"],
        "travel_date": ["2024-01-01", "2024-01-01"],
        "target_demand": [150.0, 80.0],
    })

    df_rec = HierarchicalReconciler.top_down_reconcile(df_entity, dest_totals)

    # Reconciled forecasts for D1: E1 = 40 * 1.5 = 60, E2 = 60 * 1.5 = 90 (Sum = 150)
    d1_sum = df_rec[df_rec["destination_id"] == "D1"]["q_50_reconciled"].sum()
    assert np.isclose(d1_sum, 150.0, atol=0.1)

    # Reconciled forecasts for D2: E3 = 30 * 0.8 = 24, E4 = 70 * 0.8 = 56 (Sum = 80)
    d2_sum = df_rec[df_rec["destination_id"] == "D2"]["q_50_reconciled"].sum()
    assert np.isclose(d2_sum, 80.0, atol=0.1)


def test_forecast_evaluator_metrics() -> None:
    evaluator = ForecastEvaluator()
    y_true = np.array([100.0, 200.0, 300.0])
    y_pred = np.array([110.0, 190.0, 310.0])

    wmape = evaluator.wmape(y_true, y_pred)
    assert np.isclose(wmape, 30.0 / 600.0)

    bias = evaluator.forecast_bias(y_true, y_pred)
    assert np.isclose(bias, 10.0 / 600.0)

    coverage = evaluator.interval_coverage(
        y_true=y_true,
        q_low=np.array([90.0, 180.0, 290.0]),
        q_high=np.array([120.0, 220.0, 320.0]),
    )
    assert coverage == 1.0
