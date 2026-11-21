"""Unit tests for demand censoring and look-to-book correction."""

from datetime import date
import pandas as pd
from inveniq_pipelines.censoring.tobit_correction import DemandCensoringCorrection


def test_inverse_mills_ratio_right_censored() -> None:
    c = 100.0
    mu = 110.0
    sigma = 15.0
    expected_truncated = DemandCensoringCorrection.inverse_mills_ratio_right_censored(c, mu, sigma)

    # When censored at c=100 with mu=110, E[D | D >= 100] must exceed c and mu
    assert expected_truncated > c
    assert expected_truncated >= mu


def test_uncensor_demand_pipeline() -> None:
    correction = DemandCensoringCorrection()

    df_bookings = pd.DataFrame([
        {
            "booking_id": "B1",
            "entity_id": "HTL_001",
            "destination_id": "DEST_GOA",
            "product_type": "HOTEL",
            "travel_date": date(2024, 1, 1),
            "quantity": 50,
            "sell_price_inr": 8000.0,
            "cancelled_flag": False,
        },
        {
            "booking_id": "B2",
            "entity_id": "HTL_001",
            "destination_id": "DEST_GOA",
            "product_type": "HOTEL",
            "travel_date": date(2024, 1, 2),
            "quantity": 20,
            "sell_price_inr": 7500.0,
            "cancelled_flag": False,
        },
    ])

    df_searches = pd.DataFrame([
        {
            "search_id": "S1",
            "entity_id": "HTL_001",
            "destination_id": "DEST_GOA",
            "travel_date": date(2024, 1, 1),
            "results_shown": 2500,
            "bookings_count": 50,
        },
        {
            "search_id": "S2",
            "entity_id": "HTL_001",
            "destination_id": "DEST_GOA",
            "travel_date": date(2024, 1, 2),
            "results_shown": 600,
            "bookings_count": 20,
        },
    ])

    # Date 2024-01-01 was sold out at capacity 50!
    df_soldouts = pd.DataFrame([
        {
            "soldout_id": "SLD_1",
            "entity_id": "HTL_001",
            "destination_id": "DEST_GOA",
            "travel_date": date(2024, 1, 1),
            "allotment_capacity": 50,
            "estimated_lost_demand": 25.0,
            "unmet_searches": 700,
        }
    ])

    df_uncensored = correction.uncensor_demand(df_bookings, df_searches, df_soldouts)

    assert len(df_uncensored) == 2

    # Sold-out row
    row_soldout = df_uncensored[df_uncensored["travel_date"] == date(2024, 1, 1)].iloc[0]
    assert row_soldout["is_censored"] is True or row_soldout["is_censored"] == 1
    assert row_soldout["uncensored_demand"] >= row_soldout["observed_bookings"]
    assert row_soldout["demand_uplift"] >= 0.0

    # Non-soldout row
    row_normal = df_uncensored[df_uncensored["travel_date"] == date(2024, 1, 2)].iloc[0]
    assert row_normal["is_censored"] is False or row_normal["is_censored"] == 0
    assert row_normal["uncensored_demand"] == row_normal["observed_bookings"]
    assert row_normal["demand_uplift"] == 0.0
