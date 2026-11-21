"""Unit tests for Stochastic MILP + CVaR Optimization Engine."""

import numpy as np
import pandas as pd
from inveniq_optimizer.engine.solver import StochasticOptimizer
from inveniq_optimizer.postprocessing.frontier import EfficientFrontierEngine
from inveniq_optimizer.postprocessing.sensitivity import SensitivityEngine


def get_sample_candidates() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "entity_id": "HTL_GOA_001",
            "destination_id": "DEST_GOA",
            "supplier_id": "SUP_001",
            "product_type": "HOTEL",
            "cost_price_inr": 5000.0,
            "sell_price_inr": 7000.0,
            "allotment_size": 40,
            "min_order_qty": 5,
            "q_10": 20.0,
            "q_50": 35.0,
            "q_90": 55.0,
            "cancel_prob": 0.08,
            "release_cutoff_days": 14,
        },
        {
            "entity_id": "HTL_GOA_002",
            "destination_id": "DEST_GOA",
            "supplier_id": "SUP_002",
            "product_type": "HOTEL",
            "cost_price_inr": 8000.0,
            "sell_price_inr": 11000.0,
            "allotment_size": 30,
            "min_order_qty": 3,
            "q_10": 15.0,
            "q_50": 25.0,
            "q_90": 40.0,
            "cancel_prob": 0.06,
            "release_cutoff_days": 21,
        },
        {
            "entity_id": "FLT_DEL_GOI_01",
            "destination_id": "DEST_GOA",
            "supplier_id": "SUP_003",
            "product_type": "FLIGHT",
            "cost_price_inr": 4500.0,
            "sell_price_inr": 6000.0,
            "allotment_size": 50,
            "min_order_qty": 10,
            "q_10": 25.0,
            "q_50": 45.0,
            "q_90": 60.0,
            "cancel_prob": 0.05,
            "release_cutoff_days": 7,
        },
        {
            "entity_id": "HTL_DXB_001",
            "destination_id": "DEST_DUBAI",
            "supplier_id": "SUP_001",
            "product_type": "HOTEL",
            "cost_price_inr": 12000.0,
            "sell_price_inr": 16000.0,
            "allotment_size": 25,
            "min_order_qty": 5,
            "q_10": 10.0,
            "q_50": 20.0,
            "q_90": 30.0,
            "cancel_prob": 0.07,
            "release_cutoff_days": 28,
        },
    ])


def test_stochastic_optimizer_budget_and_allotment_invariants() -> None:
    candidates = get_sample_candidates()
    budget = 400_000.0  # ₹4 Lakh budget

    optimizer = StochasticOptimizer(
        budget_inr=budget,
        risk_appetite="BALANCED",
        dest_exposure_cap=0.80,
        supplier_exposure_cap=0.60,
        target_scenarios=20,
    )
    solution = optimizer.optimize(candidates)

    assert solution["status"] == "OPTIMAL"
    assert solution["total_capital_committed_inr"] <= budget + 1e-4

    # Verify MOQs and Allotments
    for rec in solution["recommendations"]:
        q = rec["procure_quantity"]
        assert q >= rec["min_order_qty"]
        assert q <= rec["allotment_available"]
        assert q > 0

    assert solution["expected_profit_inr"] > 0
    assert solution["expected_roi_pct"] > 0


def test_efficient_frontier_generation() -> None:
    candidates = get_sample_candidates()
    optimizer = StochasticOptimizer(budget_inr=500_000.0, target_scenarios=15)
    frontier_engine = EfficientFrontierEngine(optimizer)

    points = frontier_engine.compute_frontier(candidates, num_points=3)
    assert len(points) == 3

    # As lambda increases (more conservative), expected profit decreases or stays same, risk decreases
    assert all("expected_profit_inr" in pt for pt in points)
    assert all("cvar_loss_inr" in pt for pt in points)


def test_sensitivity_engine() -> None:
    candidates = get_sample_candidates()
    optimizer = StochasticOptimizer(budget_inr=500_000.0, target_scenarios=15)
    sens_engine = SensitivityEngine(optimizer)

    results = sens_engine.compute_budget_sensitivity(candidates, multipliers=[0.8, 1.0, 1.2])
    assert len(results) == 3
    # Higher budget should enable higher total profit
    assert results[2]["expected_profit_inr"] >= results[0]["expected_profit_inr"]
