"""Unit tests for model registry and champion-challenger promotion."""

import tempfile
from pathlib import Path
from inveniq_ml.registry.mlflow_client import ModelRegistry


def test_champion_challenger_promotion_logic() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        reg_file = Path(tmp_dir) / "registry.json"
        registry = ModelRegistry(registry_file=reg_file)

        # 1. Register baseline model
        registry.register_model_run(
            model_name="demand_forecaster",
            version="v1.0",
            metrics={"wmape": 0.45, "smape": 42.0},
            parameters={"model": "seasonal_naive"},
        )

        # First model should be auto-promoted to Champion
        promoted = registry.evaluate_champion_challenger("demand_forecaster:v1.0")
        assert promoted is True

        # 2. Register inferior challenger
        registry.register_model_run(
            model_name="demand_forecaster",
            version="v1.1",
            metrics={"wmape": 0.46, "smape": 43.0},
            parameters={"model": "rolling_mean"},
        )
        # Should NOT be promoted
        promoted_v11 = registry.evaluate_champion_challenger("demand_forecaster:v1.1")
        assert promoted_v11 is False

        # 3. Register superior challenger (LightGBM with 0.14 WMAPE)
        registry.register_model_run(
            model_name="demand_forecaster",
            version="v2.0",
            metrics={"wmape": 0.14, "smape": 13.9},
            parameters={"model": "quantile_lightgbm"},
        )
        # Should be promoted to Champion!
        promoted_v20 = registry.evaluate_champion_challenger("demand_forecaster:v2.0")
        assert promoted_v20 is True

        # Verify registry state
        data = registry._load_registry()
        assert data["production_champion"] == "demand_forecaster:v2.0"
        assert data["models"]["demand_forecaster:v1.0"]["stage"] == "Archived"
        assert data["models"]["demand_forecaster:v2.0"]["stage"] == "Production"
