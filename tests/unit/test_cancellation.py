"""Unit tests for calibrated cancellation model and cutoff timing."""

import numpy as np
import pandas as pd
from inveniq_ml.cancellation.cancellation_model import CalibratedCancellationModel


def test_calibrated_cancellation_model_fit_and_predict() -> None:
    np.random.seed(42)
    n = 250

    leads = np.random.exponential(14, n).astype(int) + 1
    prices = np.random.uniform(2000, 15000, n)
    ptypes = np.random.choice(["HOTEL", "FLIGHT"], n)

    # Longer lead time leads to higher cancellation probability
    cancel_prob = np.clip(0.04 + (leads / 90.0) * 0.25, 0.02, 0.50)
    cancelled = np.random.binomial(1, cancel_prob)

    df_bookings = pd.DataFrame({
        "lead_time_days": leads,
        "quantity": np.random.choice([1, 2, 4], n),
        "sell_price_inr": prices,
        "cost_price_inr": prices * 0.8,
        "product_type": ptypes,
        "destination_id": np.random.choice(["DEST_GOA", "DEST_DUBAI"], n),
        "supplier_id": np.random.choice(["SUP_001", "SUP_002"], n),
        "cancelled_flag": cancelled,
    })

    model = CalibratedCancellationModel(num_boost_round=15)
    X, y, cols = model.prepare_training_features(df_bookings)

    model.fit(X, y)
    probs = model.predict_probability(X)

    # Probabilities must be properly bounded in [0.01, 0.99]
    assert len(probs) == n
    assert (probs >= 0.01).all()
    assert (probs <= 0.99).all()

    # Evaluation metrics
    metrics = model.evaluate(X, y)
    assert "roc_auc" in metrics
    assert "brier_score" in metrics
    assert 0.0 <= metrics["brier_score"] <= 0.25


def test_estimate_timing_relative_to_cutoff() -> None:
    timing = CalibratedCancellationModel.estimate_timing_relative_to_cutoff(
        cancel_prob=0.15,
        lead_time_days=30,
        release_cutoff_days=14,
    )
    assert timing["total_cancel_prob"] == 0.15
    assert timing["p_cancel_before_cutoff"] > 0.0
    assert timing["p_cancel_after_cutoff"] > 0.0
    assert np.isclose(
        timing["p_cancel_before_cutoff"] + timing["p_cancel_after_cutoff"],
        0.15,
        atol=1e-4,
    )

    # When booked inside cutoff window (lead_time <= cutoff)
    timing_inside = CalibratedCancellationModel.estimate_timing_relative_to_cutoff(
        cancel_prob=0.10,
        lead_time_days=7,
        release_cutoff_days=14,
    )
    assert timing_inside["p_cancel_before_cutoff"] == 0.0
    assert timing_inside["p_cancel_after_cutoff"] == 0.10
