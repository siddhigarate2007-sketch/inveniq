# InvenIQ Production Operations Runbook

**Service Name:** InvenIQ B2B Travel Inventory Optimization Engine  
**Tier:** Mission-Critical (Tier 1 Financial Decision Support)  
**Owners:** Revenue Science & SRE Team  
**Escalation Pager:** `oncall-inveniq@tbo.com`

---

## 1. Production SLA Targets & Alert Thresholds

| Metric | Target SLA | Warning Threshold | Critical Escalation |
| :--- | :--- | :--- | :--- |
| **API Read Latency (p95)** | < 300 ms | > 300 ms for 2m | > 800 ms for 5m |
| **Optimization Solver Run** | < 60 seconds | > 30 seconds | > 60 seconds or Timeout |
| **Solver Failure Rate** | 0.0% (Infeasible=0) | 1 failure | &ge; 2 failures in 10m |
| **Forecasting WMAPE** | < 18.0% | > 20.0% | > 25.0% |
| **Feature PSI Drift** | < 0.10 | 0.10 &le; PSI &le; 0.20 | PSI > 0.25 |
| **Portfolio CVaR / Budget** | < 10.0% | > 12.0% | > 15.0% |

---

## 2. Incident Response Playbooks

### Playbook 1: Solver Fails or Reports Infeasible (`OptimizationSolverFailure`)
- **Symptoms:** User receives `FAILED` status or solver throws `Infeasible or Unbounded`.
- **Root Cause Analysis:**
  1. Check constraints: Total budget might be smaller than required MOQs across mandatory allotments.
  2. Check exposure caps: Sum of minimum order quantities in a single destination may exceed `dest_exposure_cap * budget`.
- **Resolution Steps:**
  1. Inspect solver log: `docker logs inveniq-api --tail 100` or grep `scipy.optimize.milp` status code.
  2. If status code is 2 (Infeasible), inspect candidate items with high `min_order_qty`.
  3. Relax the exposure cap to 45% or increase minimum budget bound.
  4. Fall back to greedy heuristic baseline if emergency pre-buy execution is required immediately.

### Playbook 2: High API Latency (`HighApiLatencyP95`)
- **Symptoms:** P95 response time exceeds 300ms on `/api/v1/optimization/runs` or `/api/v1/inventory/candidates`.
- **Resolution Steps:**
  1. Verify DuckDB lakehouse file lock: Ensure lakehouse views in `data/lakehouse/inveniq_lake.duckdb` are opened in read-only mode (`duckdb.connect(read_only=True)`).
  2. Check memory usage: If worker thread pool is saturated with long scenario simulations, scale worker replicas in Kubernetes (`kubectl scale deployment inveniq-worker --replicas=4`).

### Playbook 3: Feature Drift Alert Triggered (`FeatureDriftDetected`)
- **Symptoms:** Prometheus fires alert `inveniq_feature_drift_psi > 0.25`.
- **Root Cause Analysis:** Search patterns shifted drastically due to unexpected geopolitical announcements, airline strikes, or unseasonal monsoon storms.
- **Resolution Steps:**
  1. Run automated drift assessment:
     ```bash
     python -m inveniq_ml.monitoring.drift_monitor
     ```
  2. Inspect drifting features (e.g. `look_to_book_ratio`, `search_volume_lag7`).
  3. Trigger automated model retraining on recent 30-day window:
     ```bash
     python -m inveniq_ml.forecasting.pipeline --retrain-trigger=drift
     ```
  4. Compare challenger WMAPE against current champion. If challenger WMAPE improves by &ge; 2.0% relative, promote via MLflow model registry:
     ```bash
     python -m inveniq_ml.registry.mlflow_client --promote
     ```

---

## 3. Disaster Recovery & Backup Procedures

### 3.1 Lakehouse Parquet Snapshot
- InvenIQ stores historical facts and dimensional entities as immutable Parquet files in `data/lakehouse/`.
- Automated daily S3/MinIO snapshot schedule:
  ```bash
  aws s3 sync /app/data/lakehouse/ s3://tbo-inveniq-backups/lakehouse/$(date +%Y%m%d)/
  ```

### 3.2 State Store & Audit Log Recovery
- All financial approval decisions and audit trail logs are replicated to PostgreSQL `inveniq_db`.
- To restore state from cold backup:
  ```bash
  pg_restore -h postgres -U inveniq_user -d inveniq_db /backups/inveniq_backup_latest.dump
  ```

### 3.3 Zero-Downtime Rollback
- If a promoted ML model underperforms in production:
  ```bash
  # Instantly demote model to Staging and reactivate last-known-good champion
  python -m inveniq_ml.registry.mlflow_client --rollback
  ```
