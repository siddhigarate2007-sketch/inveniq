"""Unit tests for Prometheus metrics exporter and drift monitor."""

import numpy as np
import pandas as pd
from inveniq_api.monitoring.metrics import metrics_collector
from inveniq_ml.monitoring.drift_monitor import DriftMonitor


def test_metrics_collector_recording_and_export():
    """Verifies that HTTP requests and optimization metrics are exported in Prometheus format."""
    metrics_collector.record_request("POST", "/api/v1/optimization/runs", 202, 0.045)
    metrics_collector.record_optimization_run(
        status="COMPLETED_AWAITING_APPROVAL",
        risk_appetite="BALANCED",
        duration_seconds=0.25,
        budget_inr=50000000.0,
        profit_inr=9840000.0,
        cvar_inr=1420000.0,
    )

    text = metrics_collector.export_prometheus_text()
    assert "inveniq_http_requests_total" in text
    assert 'method="POST"' in text
    assert "inveniq_optimization_runs_total" in text
    assert "inveniq_budget_allocated_inr 50000000.0" in text
    assert "inveniq_expected_profit_inr 9840000.0" in text
    assert "inveniq_cvar_risk_inr 1420000.0" in text


def test_drift_monitor_psi_and_ks_stable():
    """Verifies that identical distributions report low PSI and no drift."""
    rng = np.random.default_rng(42)
    ref = rng.normal(100, 15, size=1000)
    cur = rng.normal(100, 15, size=1000)

    monitor = DriftMonitor()
    psi = monitor.calculate_psi(ref, cur)
    assert psi < 0.10  # Must be healthy

    df_ref = pd.DataFrame({"search_vol": ref})
    df_cur = pd.DataFrame({"search_vol": cur})
    reports = monitor.assess_feature_drift(df_ref, df_cur, ["search_vol"])
    assert len(reports) == 1
    assert not reports[0].drift_detected
    assert "HEALTHY" in reports[0].action_required


def test_drift_monitor_psi_drift_detected():
    """Verifies that a distribution shift triggers drift alert."""
    rng = np.random.default_rng(42)
    ref = rng.normal(100, 15, size=1000)
    cur = rng.normal(160, 25, size=1000)  # Significant mean and variance shift

    monitor = DriftMonitor()
    psi = monitor.calculate_psi(ref, cur)
    assert psi > 0.20

    df_ref = pd.DataFrame({"search_vol": ref})
    df_cur = pd.DataFrame({"search_vol": cur})
    reports = monitor.assess_feature_drift(df_ref, df_cur, ["search_vol"])
    assert reports[0].drift_detected
    assert "TRIGGER_RETRAINING" in reports[0].action_required
