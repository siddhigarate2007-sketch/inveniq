"""Unit tests for feature engineering and leakage prevention."""

from datetime import date, timedelta
import numpy as np
import pandas as pd
from inveniq_ml.features.builder import FeaturePipeline


def test_feature_pipeline_zero_leakage() -> None:
    # Construct synthetic daily series for 1 entity
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(50)]
    demands = [10.0 + i * 2.0 for i in range(50)]

    df_raw = pd.DataFrame({
        "travel_date": dates,
        "entity_id": ["HTL_001"] * 50,
        "destination_id": ["DEST_GOA"] * 50,
        "product_type": ["HOTEL"] * 50,
        "observed_bookings": demands,
        "uncensored_demand": demands,
        "is_censored": [0] * 50,
        "searches_count": [500] * 50,
        "avg_sell_price_inr": [5000.0] * 50,
        "day_of_week": [d.weekday() for d in dates],
        "is_weekend": [int(d.weekday() in (5, 6)) for d in dates],
        "is_holiday": [0] * 50,
        "is_festival": [0] * 50,
        "is_school_vacation": [0] * 50,
        "is_long_weekend": [0] * 50,
        "country": ["India"] * 50,
        "region": ["West"] * 50,
        "dest_tier": [2] * 50,
        "domestic_flag": [1] * 50,
        "avg_temp_celsius": [28.0] * 50,
        "rainfall_mm": [0.0] * 50,
        "competitor_price_index": [100.0] * 50,
        "fx_rate_usd_inr": [83.0] * 50,
        "fuel_price_index": [105.0] * 50,
        "search_trend_index": [50.0] * 50,
    })

    pipeline = FeaturePipeline()
    df_feat = pipeline.transform_features(df_raw)

    # Check lag_7 strictly matches demand from 7 days prior
    for i in range(10, 50):
        expected_lag7 = demands[i - 7]
        actual_lag7 = df_feat.iloc[i]["lag_7"]
        assert actual_lag7 == expected_lag7, f"Leakage detected at row {i}: {actual_lag7} != {expected_lag7}"

    # Check rolling mean 7 uses shifted values (does NOT include current day demand)
    for i in range(10, 50):
        expected_rolling = np.mean(demands[i - 7 : i])
        actual_rolling = df_feat.iloc[i]["rolling_mean_7"]
        assert np.isclose(actual_rolling, expected_rolling), f"Rolling leakage at row {i}"


def test_cyclical_calendar_encodings() -> None:
    pipeline = FeaturePipeline()
    df_raw = pd.DataFrame({
        "travel_date": [date(2024, 1, 1), date(2024, 7, 1)],
        "entity_id": ["E1", "E1"],
        "destination_id": ["D1", "D1"],
        "product_type": ["HOTEL", "HOTEL"],
        "observed_bookings": [10.0, 10.0],
        "uncensored_demand": [10.0, 10.0],
        "is_censored": [0, 0],
        "searches_count": [100, 100],
        "avg_sell_price_inr": [1000.0, 1000.0],
        "day_of_week": [0, 0],
        "is_weekend": [0, 0],
        "is_holiday": [0, 0],
        "is_festival": [0, 0],
        "is_school_vacation": [0, 0],
        "is_long_weekend": [0, 0],
        "country": ["India", "India"],
        "region": ["West", "West"],
        "dest_tier": [1, 1],
        "domestic_flag": [1, 1],
        "avg_temp_celsius": [25.0, 25.0],
        "rainfall_mm": [0.0, 0.0],
        "competitor_price_index": [100.0, 100.0],
        "fx_rate_usd_inr": [83.0, 83.0],
        "fuel_price_index": [100.0, 100.0],
        "search_trend_index": [50.0, 50.0],
    })

    df_feat = pipeline.transform_features(df_raw)
    assert "sin_doy" in df_feat.columns
    assert "cos_doy" in df_feat.columns
    assert -1.0 <= df_feat["sin_doy"].min() <= 1.0
    assert -1.0 <= df_feat["cos_doy"].max() <= 1.0
