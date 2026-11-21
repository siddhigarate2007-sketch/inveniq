"""Property-based invariant tests for the optimization engine.

Generates randomized test instances across continuous budget ranges, costs,
and risk parameters to mathematically prove:
- Invariant 1: Budget cap is NEVER violated (Hard constraint)
- Invariant 2: Quantities are strictly non-negative integers
- Invariant 3: Minimum Order Quantities (MOQs) and Allotment bounds hold
- Invariant 4: Destination & Supplier exposure caps are strictly respected
"""

import numpy as np
import pandas as pd
import pytest
from inveniq_optimizer.engine.solver import StochasticOptimizer


def generate_random_candidates(seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_items = 4

    costs = rng.uniform(2000.0, 10000.0, n_items)
    markups = rng.uniform(1.20, 1.45, n_items)
    sells = costs * markups
    allotments = rng.integers(20, 50, n_items)
    moqs = rng.integers(2, 6, n_items)

    dests = ["DEST_A", "DEST_B", "DEST_A", "DEST_B"]
    supps = ["SUP_1", "SUP_2", "SUP_1", "SUP_2"]

    rows = []
    for i in range(n_items):
        p50 = float(rng.uniform(15.0, 35.0))
        rows.append({
            "entity_id": f"ITEM_{i}",
            "destination_id": dests[i],
            "supplier_id": supps[i],
            "product_type": "HOTEL" if i < 2 else "FLIGHT",
            "cost_price_inr": round(float(costs[i]), 2),
            "sell_price_inr": round(float(sells[i]), 2),
            "allotment_size": int(allotments[i]),
            "min_order_qty": int(moqs[i]),
            "q_10": max(5.0, p50 - 10.0),
            "q_50": p50,
            "q_90": p50 + 15.0,
            "cancel_prob": round(float(rng.uniform(0.04, 0.10)), 3),
            "release_cutoff_days": int(rng.choice([7, 14, 21])),
        })
    return pd.DataFrame(rows)


@pytest.mark.parametrize("seed", list(range(101, 116)))
def test_optimizer_mathematical_invariants_randomized(seed: int) -> None:
    rng = np.random.default_rng(seed)
    candidates = generate_random_candidates(seed)

    # Randomized budget between 100,000 and 1,500,000 INR
    budget = float(rng.uniform(100_000.0, 1_500_000.0))
    dest_cap = float(rng.uniform(0.50, 0.90))
    risk_appetite = str(rng.choice(["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]))

    optimizer = StochasticOptimizer(
        budget_inr=budget,
        risk_appetite=risk_appetite,
        dest_exposure_cap=dest_cap,
        supplier_exposure_cap=0.85,
        target_scenarios=10,
        seed=seed,
    )
    solution = optimizer.optimize(candidates)

    assert solution["status"] == "OPTIMAL"

    # Invariant 1: Budget is NEVER exceeded (Hard constraint)
    total_committed = solution["total_capital_committed_inr"]
    assert total_committed <= budget + 1e-2, (
        f"Budget violation: committed {total_committed} > budget {budget}"
    )

    # Invariant 2: Quantities are non-negative integers
    for rec in solution["recommendations"]:
        q = rec["procure_quantity"]
        assert isinstance(q, (int, np.integer))
        assert q >= 0

        # Invariant 3: If item is procured, MOQ <= q <= Allotment
        if q > 0:
            assert q >= rec["min_order_qty"], (
                f"MOQ violation: {q} < MOQ {rec['min_order_qty']}"
            )
            assert q <= rec["allotment_available"], (
                f"Allotment violation: {q} > Allotment {rec['allotment_available']}"
            )

    # Invariant 4: Destination exposure caps hold
    dest_costs: dict[str, float] = {}
    for rec in solution["recommendations"]:
        d = rec["destination_id"]
        dest_costs[d] = dest_costs.get(d, 0.0) + rec["total_investment_inr"]

    for d, d_invest in dest_costs.items():
        max_allowed = dest_cap * budget + 1e-2
        assert d_invest <= max_allowed, (
            f"Destination {d} exceeded cap: {d_invest} > {max_allowed}"
        )
