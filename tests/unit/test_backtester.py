"""Unit tests for walk-forward backtester and stress testing."""

import numpy as np
import pandas as pd
from inveniq_optimizer.backtest.backtester import StressTestEngine, WalkForwardBacktester
from inveniq_optimizer.engine.solver import StochasticOptimizer


def test_walk_forward_backtest_beats_baselines() -> None:
    # Heterogeneous inventory: some high-demand winners, some low-demand traps
    candidates = pd.DataFrame([
        {
            "entity_id": "HTL_WINNER_1",
            "destination_id": "DEST_GOA",
            "supplier_id": "SUP_1",
            "product_type": "HOTEL",
            "cost_price_inr": 5000.0,
            "sell_price_inr": 8000.0,  # High margin
            "allotment_size": 30,
            "min_order_qty": 2,
            "q_10": 20.0,
            "q_50": 30.0,
            "q_90": 45.0,
            "cancel_prob": 0.04,
            "release_cutoff_days": 14,
            "lag_365": 25.0,
        },
        {
            "entity_id": "HTL_WINNER_2",
            "destination_id": "DEST_DUBAI",
            "supplier_id": "SUP_2",
            "product_type": "HOTEL",
            "cost_price_inr": 6000.0,
            "sell_price_inr": 9500.0,  # High margin
            "allotment_size": 25,
            "min_order_qty": 2,
            "q_10": 15.0,
            "q_50": 25.0,
            "q_90": 35.0,
            "cancel_prob": 0.05,
            "release_cutoff_days": 21,
            "lag_365": 20.0,
        },
        {
            "entity_id": "HTL_TRAP_1",
            "destination_id": "DEST_GOA",
            "supplier_id": "SUP_1",
            "product_type": "HOTEL",
            "cost_price_inr": 5000.0,
            "sell_price_inr": 5500.0,  # Low margin, low demand
            "allotment_size": 30,
            "min_order_qty": 2,
            "q_10": 2.0,
            "q_50": 5.0,
            "q_90": 8.0,
            "cancel_prob": 0.15,
            "release_cutoff_days": 7,
            "lag_365": 25.0,  # Last year had high volume, but this year demand collapsed
        },
        {
            "entity_id": "HTL_TRAP_2",
            "destination_id": "DEST_DUBAI",
            "supplier_id": "SUP_2",
            "product_type": "HOTEL",
            "cost_price_inr": 6000.0,
            "sell_price_inr": 6500.0,  # Low margin, low demand
            "allotment_size": 25,
            "min_order_qty": 2,
            "q_10": 1.0,
            "q_50": 4.0,
            "q_90": 6.0,
            "cancel_prob": 0.18,
            "release_cutoff_days": 7,
            "lag_365": 20.0,
        },
    ])

    # Realized demands: Winners have high demand (30, 25), Traps collapse to (4, 3)
    actual_demands = np.array([30.0, 25.0, 4.0, 3.0])

    optimizer = StochasticOptimizer(
        budget_inr=300_000.0,
        risk_appetite="AGGRESSIVE",
        dest_exposure_cap=0.65,
        supplier_exposure_cap=0.65,
        target_scenarios=20,
    )
    backtester = WalkForwardBacktester(optimizer)

    report = backtester.run_backtest(candidates, actual_demands)
    assert report["status"] == "SUCCESS"
    assert len(report["strategies_evaluated"]) == 5

    # InvenIQ profit should exceed last year baseline by avoiding the traps
    inveniq_res = report["strategies_evaluated"][0]
    last_year_res = report["strategies_evaluated"][1]
    assert inveniq_res["realized_profit_inr"] > last_year_res["realized_profit_inr"]
    assert inveniq_res["unsold_inventory_loss_inr"] < last_year_res["unsold_inventory_loss_inr"]


def test_stress_testing_engine() -> None:
    candidates = pd.DataFrame([
        {
            "entity_id": f"ITEM_{i}",
            "destination_id": "DEST_GOA",
            "supplier_id": "SUP_001",
            "product_type": "HOTEL",
            "cost_price_inr": 5000.0,
            "sell_price_inr": 7000.0,
            "allotment_size": 30,
            "min_order_qty": 2,
            "q_10": 15.0,
            "q_50": 25.0,
            "q_90": 40.0,
            "cancel_prob": 0.05,
            "release_cutoff_days": 14,
        }
        for i in range(4)
    ])
    demands = np.array([25.0, 25.0, 25.0, 25.0])

    optimizer = StochasticOptimizer(budget_inr=200_000.0, target_scenarios=15)
    stress_engine = StressTestEngine(optimizer)

    stress_results = stress_engine.run_stress_tests(candidates, demands)
    assert len(stress_results) == 5

    # Nominal scenario should have higher profit than the severe -20% demand shock
    nominal = stress_results[0]
    demand_shock = stress_results[1]
    assert nominal["realized_profit_inr"] >= demand_shock["realized_profit_inr"]
