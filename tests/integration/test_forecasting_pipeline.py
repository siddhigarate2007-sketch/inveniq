"""Integration test verifying end-to-end demand forecasting pipeline."""

from inveniq_ml.forecasting.pipeline import DemandForecastingPipeline


def test_demand_forecasting_pipeline_end_to_end() -> None:
    pipeline = DemandForecastingPipeline()
    report = pipeline.run_pipeline()

    assert report["status"] == "SUCCESS"
    assert report["test_sample_size"] > 0

    # 1. LightGBM must outperform Seasonal Naive baseline on WMAPE
    lgbm_wmape = report["lightgbm_conformal"]["wmape"]
    naive_wmape = report["baselines"]["seasonal_naive"]["wmape"]
    assert lgbm_wmape < naive_wmape, f"LightGBM ({lgbm_wmape}) did not beat Naive ({naive_wmape})"

    # 2. Conformal Coverage must be close to target 80% coverage
    coverage_80 = report["lightgbm_conformal"]["coverage_80"]
    assert coverage_80 >= 0.70, f"Conformal coverage too low: {coverage_80}"

    # 3. Ground truth recovery: models must capture positive festival demand lift
    fest_lift = report["ground_truth_recovery"]["festival_lift_recovered_pct"]
    assert fest_lift > 20.0, f"Festival lift was not recovered: {fest_lift}%"

    # 4. Segment breakdown must be generated
    assert len(report["segment_breakdown"]) > 0
    assert len(report["top_features"]) > 0
