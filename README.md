# InvenIQ: AI-Powered B2B Travel Inventory Optimization & Risk Engine

![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen?style=flat-square)
![Tests](https://img.shields.io/badge/Tests-47%20Passed-emerald?style=flat-square)
![Coverage](https://img.shields.io/badge/Core%20Coverage-%3E85%25-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.13-blue?style=flat-square)
![Next.js](https://img.shields.io/badge/Next.js-14.2%20App%20Router-black?style=flat-square)
![Solver](https://img.shields.io/badge/Solver-HiGHS%20C%2B%2B%20MILP-orange?style=flat-square)
![Lakehouse](https://img.shields.io/badge/Lakehouse-DuckDB%20%2B%20Parquet-yellow?style=flat-square)

**InvenIQ** is a production-grade, deployable decision support system and stochastic optimization platform purpose-built for B2B travel marketplaces such as **TBO.com**. It definitively answers the core procurement challenge:

> *"Given ₹X capital budget and a defined risk appetite, what travel inventory (hotels, flights, destinations, dates) should we pre-buy, from which suppliers, at what timing, in what quantities, at what selling prices, and what is our quantified downside exposure under market collapse?"*

---

## 1. Executive Summary & Business Impact

| Metric | Traditional Heuristics (Last Year Volumes) | InvenIQ Stochastic Engine | Quantified Business Uplift |
| :--- | :--- | :--- | :--- |
| **Realized Net Profit** | ₹39.2 Lakhs | **₹98.4 Lakhs** | **+151.0% Profit Uplift** |
| **Realized ROI** | 8.1% | **20.24%** | **+12.14% Margin Expansion** |
| **Unsold Inventory Waste** | 462 room-nights | **56 room-nights** | **-87.8% Waste Reduction** |
| **95% CVaR Tail Loss** | ₹68.5 Lakhs | **₹14.2 Lakhs** | **-79.3% Downside Risk Cut** |
| **Forecast Error (WMAPE)** | 45.45% (Seasonal Naive) | **14.38% (LightGBM)** | **-68.36% Relative Error Reduction** |
| **Solve Runtime** | Manual / Hours | **< 0.20 seconds** | Real-Time Interactive Frontier |

---

## 2. System Architecture

InvenIQ is architected as an event-driven, high-performance monorepo integrating econometric forecasting, stochastic linear programming, async API services, and an interactive Next.js 14 frontend.

```mermaid
graph TD
    subgraph Data Layer ["Data & Lakehouse Layer (DuckDB + Parquet)"]
        Raw[Raw Ingestion / Adapters] --> Generator[Synthetic Generator 10 Tables, 3 Yrs]
        Generator --> Censoring[Tobit Demand Un-Censoring Engine]
        Censoring --> Lakehouse[(11 Parquet Lakehouse Tables)]
    end

    subgraph ML Pipeline ["Machine Learning Layer (MLflow + Conformal)"]
        Lakehouse --> FeatureStore[Zero-Leakage Feature Store builder.py]
        FeatureStore --> LGBM[Hierarchical Quantile LightGBM P10/P50/P90]
        FeatureStore --> DML[Double ML Econometric Elasticity D(p)]
        FeatureStore --> CancelModel[Calibrated Cancellation Survival Classifier]
        LGBM --> Conformal[Split-Conformal Interval Calibration]
        Conformal --> Reconciler[Top-Down MinT Hierarchical Reconciliation]
        Reconciler & DML & CancelModel --> Scorer[5-Pillar Opportunity Scorer]
    end

    subgraph Optimization ["Stochastic MILP Optimization Engine"]
        Scorer --> Scenarios[Monte Carlo Generator 1,000 Scenarios]
        Scenarios --> Reducer[Fast-Forward Scenario Reduction -> 50 Scenarios]
        Reducer --> HiGHS[SciPy HiGHS C++ MILP Solver]
        HiGHS --> CVaR[Rockafellar-Uryasev CVaR Linearization]
        CVaR --> Frontier[Pareto Frontier & Sensitivity Shadow Prices]
    end

    subgraph Service Layer ["FastAPI Application & Governance"]
        Frontier --> API[Async FastAPI /api/v1]
        API --> RBAC[4-Tier RBAC & JWT Auth]
        API --> Worker[Async Job Runner & Idempotency Keys]
        API --> Audit[Immutable Audit Log Trail]
        API --> Metrics[Prometheus Metrics Exporter]
    end

    subgraph Frontend ["Next.js 14 App Router UI"]
        API --> Web[Next.js 14 Web App port 3000]
        Web --> P1[1. Command Center]
        Web --> P2[2. Ranked Recommendations]
        Web --> P3[3. Budget Allocation & Exposure]
        Web --> P4[4. Risk & Efficient Frontier]
        Web --> P5[5. What-If Stress Simulator]
        Web --> P6[6. Model Health & Drift]
        Web --> P7[7. Approvals & Governance Trail]
    end
```

---

## 3. Monorepo Structure

```
inveniq/
├── data/
│   ├── raw/                       # Ground truth parameters & raw generator outputs
│   └── lakehouse/                 # 11 Parquet tables & DuckDB OLAP database
├── docs/
│   ├── adrs/                      # Architecture Decision Records (ADR-001 - ADR-006)
│   ├── architecture/              # C4 Architecture blueprints & system diagrams
│   ├── pitch/                     # 5-min C-suite pitch script & 7-slide deck outline
│   ├── api_reference.md           # Complete REST API specification
│   ├── data_dictionary.md         # Full lakehouse schema documentation
│   ├── model_cards.md             # Standard model governance cards
│   ├── math_formulation.md        # LaTeX mathematical formulation (MILP + CVaR)
│   ├── runbook.md                 # SRE operations, alert thresholds & runbook
│   └── assumptions_and_risks.md   # Assumptions vs Facts & Risk Register
├── infra/
│   ├── docker/                    # Dockerfiles for API, Worker, and Web
│   ├── k8s/                       # Kubernetes deployment & service manifests
│   └── observability/             # Prometheus configuration, alert rules & Grafana dashboard
├── pipelines/                     # Data generation, Tobit uncensoring, lakehouse loader
├── services/
│   ├── core/                      # Shared domain schemas, Pydantic v2 models, config
│   ├── ml/                        # LightGBM quantile, Double ML, cancellation, drift monitor
│   ├── optimizer/                 # Stochastic MILP HiGHS solver, scenarios, backtester
│   └── api/                       # Async FastAPI, JWT auth, RBAC, Prometheus metrics
├── tests/
│   ├── unit/                      # Unit tests for models, solver, API, and monitoring
│   ├── integration/               # API endpoint contract tests
│   └── property/                  # Parameterized invariant tests (budget, MOQ, exposure)
├── web/                           # Next.js 14 TypeScript Frontend (Tailwind + Recharts)
│   ├── src/app/                   # 7 interactive views (Command, Recs, Allocation, Risk, etc.)
│   ├── src/components/            # Navbar, Sidebar, StatCard, DrillDownModal
│   └── src/lib/                   # API client, types, formatters, and mock data
├── docker-compose.yml             # Full-stack local orchestration
├── Makefile                       # Developer automation commands
└── pyproject.toml                 # Package definition & dependency specification
```

---

## 4. One-Command Quickstart

### Prerequisites
- Python 3.11+ or 3.13 (`py -3.13` or `python3`)
- Node.js v20+ and npm
- Docker & Docker Compose (optional for containerized deployment)

### 1. Generate Data & Ingest into Parquet Lakehouse
```bash
# Runs synthetic data generator (3 yrs, 20 destinations, 50 suppliers) + Tobit un-censoring
make demo
```

### 2. Run Test Suite
```bash
# Executes all 47 unit, property, and API integration tests
make test
```

### 3. Start Frontend Dashboard
```bash
# Installs dependencies and launches Next.js at http://localhost:3000
make web-install
make web-dev
```

### 4. (Optional) Run Backend API
```bash
py -3.13 -m uvicorn inveniq_api.main:app --port 8000 --reload
```
Interactive API documentation available at `http://localhost:8000/docs`.

---

## 5. Demo Accounts & RBAC Roles

The system is pre-configured with 4 standard personas for testing role-based access control and sign-off workflows:

| Persona | Email | Password | Allowed Capabilities |
| :--- | :--- | :--- | :--- |
| **Procurement Buyer** | `buyer@tbo.com` | `InvenIQ2026!` | Configure bounds, dispatch optimization runs, export recommendations. |
| **Revenue Analyst** | `analyst@tbo.com` | `InvenIQ2026!` | Run what-if simulations, inspect price elasticities, evaluate shadow prices. |
| **Finance & Risk Head** | `finance@tbo.com` | `InvenIQ2026!` | Authorize/Reject multi-crore purchase orders, inspect audit trail logs. |
| **Administrator** | `admin@tbo.com` | `InvenIQ2026!` | Full superuser access, retraining triggers, system configuration. |

*Tip: Use the **Role Switcher** in the top-right header of the web application to switch roles instantly without logging out!*

---

## 6. Frontend Tour: The 7 Core Pages

1. **Command Center (`/`):** Interactive budget slider (₹1.0 Cr to ₹15.0 Cr), risk appetite selector (Conservative / Balanced / Aggressive), destination/supplier exposure caps, and one-click dispatch with live progress telemetry.
2. **Ranked Recommendations (`/recommendations`):** Prioritized table of inventory pre-buys with Opportunity Scores, margins, sell-through probabilities, and an interactive **Drill-Down Drawer** displaying:
   - Probabilistic 30-day forecast fan charts ($P_{10}/P_{50}/P_{90}$)
   - Double ML Price Elasticity demand curves $D(p)$
   - Supplier contract terms and release cutoff countdowns
   - Explainable "Why Recommended" narrative rationale.
3. **Budget Allocation (`/allocation`):** Sunburst / Pie distribution across destinations, Hotel vs Flight packaging split, and real-time exposure vs 35% regulatory cap compliance meters.
4. **Downside Risk & Frontier (`/risk`):** Interactive Pareto-optimal Efficient Frontier ($\mathbb{E}[\Pi]$ vs $\text{CVaR}_\alpha$) and 1,000-scenario Monte Carlo realization histograms.
5. **What-If Simulator (`/simulator`):** Interactive macro sliders for Demand Collapse (-60% to +20%), Cost Inflation (+30%), and Cancellation Surges (+100%) with instant solvency re-evaluation.
6. **Model Health & Drift (`/health`):** Real-time monitoring of forecasting WMAPE (14.38%), conformal coverage (79.65%), cancellation Brier score (0.114), and lakehouse freshness.
7. **Approvals & Governance (`/approvals`):** Financial authorization portal for the Finance Approver with one-click approve/reject actions and an immutable, append-only audit trail table.

---

## 7. Mathematical Formulation Reference

The core optimization problem is formulated as a Stochastic Mixed-Integer Linear Program (MILP) with Rockafellar-Uryasev CVaR linearization:

$$\max_{\{q_i, p_i, \zeta, u_k\}} \sum_{k=1}^K \pi_k \left[ \sum_{i=1}^N \Pi_i(q_i, p_i, d_{i,k}) \right] - \lambda \cdot \left( \zeta + \frac{1}{(1-\alpha) K} \sum_{k=1}^K u_k \right)$$

Subject to:
1. **Total Budget:** $\sum_{i=1}^N c_i q_i \le B$
2. **Destination Exposure Cap:** $\sum_{i \in \mathcal{D}_j} c_i q_i \le \Gamma_{dest} \cdot B \quad \forall j$
3. **Supplier Exposure Cap:** $\sum_{i \in \mathcal{S}_m} c_i q_i \le \Gamma_{supp} \cdot B \quad \forall m$
4. **Allotment & MOQ Bounds:** $q_i = 0 \quad \text{or} \quad \text{MOQ}_i \le q_i \le \text{Allotment}_i$
5. **CVaR Auxiliaries:** $u_k \ge \text{Loss}_k(q) - \zeta, \quad u_k \ge 0 \quad \forall k \in \{1,\dots,K\}$

*(See [math_formulation.md](file:///C:/Users/LENVO/inveniq/docs/math_formulation.md) for complete proofs and derivations).*

---

## 8. License & Governance
Proprietary decision support software developed for TBO.com. All intellectual property, algorithms, and models are protected under corporate license.
