"""Unit tests for price elasticity engine and demand curve generation."""

import numpy as np
import pandas as pd
from inveniq_ml.elasticity.elasticity_model import PriceElasticityEngine


def test_price_elasticity_double_ml() -> None:
    np.random.seed(42)
    n = 300

    # Simulate realistic travel dataset with price variation and controls
    segments = np.random.choice(["Luxury", "Midscale", "Budget"], n)
    is_fest = np.random.binomial(1, 0.2, n)
    tier = np.random.choice([1, 2, 3], n)

    base_prices = {"Luxury": 12000.0, "Midscale": 6000.0, "Budget": 3000.0}
    true_betas = {"Luxury": -0.85, "Midscale": -1.45, "Budget": -2.15}

    prices = []
    demands = []
    for s, f, t in zip(segments, is_fest, tier):
        bp = base_prices[s] * (1.2 if f else 1.0) * np.random.uniform(0.9, 1.1)
        # Endogenous price: higher during festival
        price = bp
        beta = true_betas[s]
        d = 50.0 * (1.5 if f else 1.0) * ((price / base_prices[s]) ** beta) * np.random.uniform(0.85, 1.15)
        prices.append(price)
        demands.append(d)

    df = pd.DataFrame({
        "avg_sell_price_inr": prices,
        "uncensored_demand": demands,
        "segment": segments,
        "is_festival": is_fest,
        "dest_tier": tier,
    })

    engine = PriceElasticityEngine()
    est = engine.fit_double_ml(df, control_cols=["is_festival", "dest_tier"])

    assert "Luxury" in est
    assert "Midscale" in est
    assert "Budget" in est

    # All price elasticity coefficients must be strictly negative!
    for seg, eps in est.items():
        assert eps < 0.0, f"Elasticity for {seg} must be negative, got {eps}"

    # Budget demand must be more elastic than Luxury demand
    assert est["Budget"] <= est["Luxury"]


def test_demand_curve_properties() -> None:
    engine = PriceElasticityEngine()
    engine.elasticities = {"Midscale": -1.5}

    demand_fn = engine.get_demand_curve(base_price=5000.0, base_demand=100.0, segment="Midscale")

    # Demand at base price must equal base demand
    assert np.isclose(demand_fn(5000.0), 100.0)

    # Higher price must lead to lower demand (monotonic downward sloping)
    assert demand_fn(6000.0) < demand_fn(5000.0)
    assert demand_fn(4000.0) > demand_fn(5000.0)


def test_optimal_monopoly_markup() -> None:
    engine = PriceElasticityEngine()
    engine.elasticities = {"Midscale": -1.5}

    # For eps = -1.5, markup = -1.5 / (1 - 1.5) = -1.5 / -0.5 = 3.0
    opt_p = engine.compute_optimal_unconstrained_price(cost_price=1000.0, segment="Midscale")
    assert np.isclose(opt_p, 3000.0)
