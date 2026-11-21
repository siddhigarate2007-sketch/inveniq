"""Unit tests for opportunity scoring and explainability engine."""

import pandas as pd
from inveniq_ml.scoring.opportunity_scorer import OpportunityScorer


def test_opportunity_scorer_single_item() -> None:
    scorer = OpportunityScorer()

    item_report = scorer.score_item(
        item_id="HTL_001",
        forecast_p10=25.0,
        forecast_p50=35.0,
        forecast_p90=50.0,
        cost_price=5000.0,
        sell_price=7000.0,  # 28.6% margin
        allotment=40,
        supplier_reliability=0.98,
        release_cutoff_days=21,
        historical_soldout_rate=0.35,
        cancel_prob=0.06,
        is_festival=True,
    )

    assert 0.0 <= item_report["opportunity_score"] <= 100.0
    assert item_report["grade"] in ["Tier-A", "Tier-B", "Tier-C"]

    # Reason codes check
    assert "HIGH_MARGIN_EXPANSION" in item_report["reason_codes"]
    assert "PEAK_DEMAND_SURGE" in item_report["reason_codes"]
    assert "RELIABLE_SUPPLIER_SAFE_CUTOFF" in item_report["reason_codes"]

    # Reason narrative string
    assert len(item_report["reason_string"]) > 20
    assert "Recommended" in item_report["reason_string"]

    # Pillar contributions
    pillars = item_report["pillar_contributions"]
    assert all(k in pillars for k in ["demand", "margin", "sell_through", "scarcity", "supplier"])


def test_opportunity_scorer_batch_ranking() -> None:
    scorer = OpportunityScorer()

    df_cand = pd.DataFrame([
        {
            "entity_id": "HTL_POOR",
            "q_10": 5.0,
            "q_50": 10.0,
            "q_90": 15.0,
            "cost_price_inr": 5000.0,
            "sell_price_inr": 5200.0,  # 3.8% margin
            "allotment_size": 50,
            "reliability_score": 0.82,
            "release_cutoff_days": 5,
            "soldout_rate": 0.05,
            "cancel_prob": 0.18,
            "is_festival": False,
        },
        {
            "entity_id": "HTL_EXCELLENT",
            "q_10": 40.0,
            "q_50": 55.0,
            "q_90": 70.0,
            "cost_price_inr": 5000.0,
            "sell_price_inr": 7200.0,  # 30.5% margin
            "allotment_size": 40,
            "reliability_score": 0.98,
            "release_cutoff_days": 28,
            "soldout_rate": 0.40,
            "cancel_prob": 0.05,
            "is_festival": True,
        },
    ])

    df_ranked = scorer.score_all_candidates(df_cand)
    assert len(df_ranked) == 2
    assert df_ranked.iloc[0]["entity_id"] == "HTL_EXCELLENT"
    assert df_ranked.iloc[1]["entity_id"] == "HTL_POOR"
    assert df_ranked.iloc[0]["opportunity_score"] > df_ranked.iloc[1]["opportunity_score"]
