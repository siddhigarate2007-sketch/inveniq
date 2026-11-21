# InvenIQ: Production Architecture & System Blueprint
**System Name:** InvenIQ (AI-Powered B2B Travel Inventory Optimization & Risk Engine)  
**Target Organization:** TBO.com (B2B Travel Marketplace)  
**Author:** Principal Engineer + Staff Data Scientist + Product Architect  
**Version:** 1.0.0 (Phase 0 Blueprint)  

---

## 1. Executive Restatement of Requirements & Problem Context

### 1.1 Business Challenge
TBO.com operates a two-sided B2B travel marketplace connecting over 159,000 travel agents, tour operators, and API buyers with global travel inventory suppliers (over 1 million hotels, airline routes, and local transfer partners). In wholesale travel, inventory procurement takes two primary forms:
1. **Dynamic / Affiliate Connect (Zero Inventory Risk):** Real-time API query and booking upon demand. Margins are modest (typically 3%–7%), and prices surge or allotment disappears during peak demand.
2. **Pre-Purchased Guaranteed Commitments ("Merchant / Wholesale Buy"):** Pre-buying blocks of hotel room-nights and flight seats ahead of season. Suppliers offer steep wholesale discounts (e.g., 20%–40% off BAR - Best Available Rate). However, TBO bears the inventory risk: unsold inventory after contract release dates or flight departure perishes with 100% loss.

### 1.2 Core Objective & The "₹X Budget" Question
The core user question addressed by InvenIQ is:
> *"Given ₹X capital budget, target travel horizons, and an approved risk tolerance, exactly what inventory (which hotels, routes, dates) should we pre-buy, from which suppliers, at what time, in what batch quantities, at what selling prices, and what is our quantified downside exposure under adverse market shocks?"*

### 1.3 Key User Personas & Primary Workflows
| User Persona | Role & Objectives | Key Questions & Interactions |
| :--- | :--- | :--- |
| **Procurement / Buying Manager** *(Primary)* | Pre-buys inventory blocks across destinations; maximizes expected profit while respecting supplier MOQs and allotments. | "Which Goa 4-star hotels should I lock in for New Year's week? What quantity guarantees high sell-through?" |
| **Revenue / Pricing Analyst** | Evaluates price elasticity, competitive price indices, markups, and dynamic pricing curves to maximize volume $\times$ margin. | "What is the optimal selling markup for Dubai peak season? What happens to demand if we increase price by 8%?" |
| **Supplier Relations Manager** | Manages supplier performance, minimum allotment commitments, credit terms, and penalty cutoffs. | "Which supplier offers the safest release cutoff window and lowest cancellation penalty for Thailand routes?" |
| **Finance / Risk Head** *(Approver)* | Mandates hard budget limits, capital allocation ceilings per country/supplier, and downside tail risk (CVaR). | "What is our 95% CVaR loss under a 20% demand collapse? Is this ₹10 Cr commitment within our risk appetite?" |

---

## 2. Facts, Assumptions, and Open Questions Register

### 2.1 FACTS (Verified from System Specification)
1. **Budget Cap:** Total committed pre-buy expenditure must never exceed the user-defined budget cap $B$.
2. **Heterogeneous Travel Inventory:** The system covers both accommodations (hotel room-nights) and transportation (airline seats) across ~20 domestic and international destinations.
3. **Multi-Horizon Decision Window:** Purchase timing must consider lead times, supplier release deadlines, and seasonal spikes.
4. **Demand Censoring Phenomenon:** Sold-out periods mask true latent market demand. Historical booking logs understate true demand during peak periods when capacity was exhausted.
5. **Probabilistic Uncertainty:** Point forecasts are insufficient; optimization must account for demand variance via calibrated quantiles (P10, P50, P90) or Monte Carlo scenario generation.
6. **Downside Risk Control:** Risk must be quantified using Conditional Value-at-Risk (CVaR) to protect against severe tail losses.
7. **Audit & Governance:** Every recommendation, modification, and approval must be permanently recorded with role-based authorization.

### 2.2 ASSUMPTIONS (Domain & Operational Realities)
1. **Contract Release Deadlines (Cutoffs):** Suppliers offer inventory blocks with a contractual release deadline (e.g., $D - 14$ days before check-in). Unsold inventory returned prior to the cutoff incurs either zero penalty or a partial restocking fee ($c_{\text{pen}} < c_{\text{cost}}$). After the cutoff, inventory is strictly non-refundable (100% loss).
2. **B2B Wholesale Price Dynamics:** Unlike B2C retail where single users buy 1-2 tickets, B2B travel agents purchase in clusters (group bookings, FIT packages). Demand exhibits discrete lumpiness.
3. **Salvage & Secondary Resale:** Unsold inventory near departure can occasionally be liquidated via distressed flash sales at salvage recovery rate $s_i \in [0.10, 0.40] \times c_{\text{cost}}$.
4. **Cancellation Dynamics:** B2B agent bookings exhibit higher cancellation rates before payment finalization. The system must account for net realized demand after cancellations.
5. **Look-to-Book Ratios as Demand Proxy:** Unconverted search traffic during sold-out periods serves as an unbiased indicator of unmet latent demand, allowing Tobit regression adjustment.
6. **Execution Timelines:** Batch optimizations must complete in $<60$ seconds for up to 500 candidate inventory items and 1,000 scenarios.

### 2.3 OPEN QUESTIONS (To be Calibrated with Real TBO Business & Supplier Contracts)
1. **Dynamic Repricing Guardrails:** In live operations, how frequently can TBO adjust selling prices on pre-bought blocks without triggering parity violations or travel agent dissatisfaction?
2. **Multi-Currency & FX Hedging:** For international inventory (e.g., Dubai, Europe, Southeast Asia), supplier commitments are denominated in USD/AED/EUR while sales are in INR. What FX hedging reserve or buffer policy applies?
3. **Cross-Inventory Cannibalization:** Does committing to a 4-star property in North Goa cannibalize organic search volume for 5-star properties in South Goa? (To be refined with cross-elasticity models in future phases).
4. **Supplier Credit Lines vs Pre-payment:** Does TBO pay 100% upfront on commitment date, or is payment phased (e.g., 20% advance deposit, 80% at release cutoff)?

---

## 3. Monorepo Directory Tree Architecture

The system is organized as a production-grade monorepo containing modular, decoupled packages and deployable services.

```text
inveniq/
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
├── Makefile                         # Unified build, test, and dev orchestration commands
├── pyproject.toml                   # Root Python workspace configuration (ruff, black, mypy, pytest)
├── README.md                        # Project overview and quick-start guide
│
├── infra/                           # Infrastructure as Code & Orchestration
│   ├── docker/
│   │   ├── Dockerfile.api           # FastAPI container image
│   │   ├── Dockerfile.worker        # Celery / Optimization worker image
│   │   ├── Dockerfile.web           # Next.js web application image
│   │   └── Dockerfile.jupyter       # Analytics sandbox image
│   ├── k8s/                         # Kubernetes manifests / Helm charts
│   │   ├── deployment-api.yaml
│   │   ├── deployment-worker.yaml
│   │   ├── service-api.yaml
│   │   └── ingress.yaml
│   └── docker-compose.yml           # Complete local environment (Postgres, Redis, MinIO, API, Worker, Web)
│
├── docs/                            # Formal documentation
│   ├── adrs/                        # Architecture Decision Records
│   │   └── ADRS.md
│   ├── architecture/                # C4 diagrams, sequence diagrams, and system blueprint
│   │   ├── phase0_system_blueprint.md
│   │   └── system_architecture.md
│   ├── data_dictionary.md           # Schema and column definitions for all data tables
│   ├── math_formulation.md          # Formal mathematical specification of MILP + CVaR and Tobit
│   └── pitch_deck.md                # 5-minute executive pitch and slide outline
│
├── services/                        # Deployable Backend Services
│   ├── core/                        # Shared domain models, configurations, and utilities
│   │   └── src/inveniq_core/
│   │       ├── __init__.py
│   │       ├── config.py            # Pydantic-settings configuration
│   │       ├── database.py          # SQLAlchemy async engine & session management
│   │       ├── logging.py           # Structlog JSON configuration
│   │       └── schemas/             # Shared Pydantic v2 domain schemas
│   │           ├── __init__.py
│   │           ├── entities.py      # Destination, Hotel, Flight, Supplier schemas
│   │           ├── optimization.py  # Run parameters, constraints, recommendation outputs
│   │           └── user.py          # Auth and role schemas
│   │
│   ├── api/                         # FastAPI Web Application
│   │   └── src/inveniq_api/
│   │       ├── __init__.py
│   │       ├── main.py              # Application entry point, CORS, middleware, routers
│   │       ├── auth/                # JWT authentication & RBAC dependency injectors
│   │       │   ├── __init__.py
│   │       │   ├── jwt.py
│   │       │   └── rbac.py
│   │       ├── routers/             # Versioned REST endpoints (/api/v1)
│   │       │   ├── __init__.py
│   │       │   ├── auth.py
│   │       │   ├── inventory.py
│   │       │   ├── optimization.py
│   │       │   ├── risk.py
│   │       │   └── health.py
│   │       └── worker/              # Celery task definitions and queue client
│   │           ├── __init__.py
│   │           ├── celery_app.py
│   │           └── tasks.py
│   │
│   ├── ml/                          # Machine Learning & Statistical Models
│   │   └── src/inveniq_ml/
│   │       ├── __init__.py
│   │       ├── features/            # Feature transformation and point-in-time extraction
│   │       │   ├── __init__.py
│   │       │   ├── builder.py
│   │       │   └── look_to_book.py
│   │       ├── forecasting/         # Hierarchical Quantile LightGBM & Conformal Calibration
│   │       │   ├── __init__.py
│   │       │   ├── lightgbm_model.py
│   │       │   ├── reconciliation.py
│   │       │   └── conformal.py
│   │       ├── elasticity/          # Price elasticity & demand curve estimation
│   │       │   ├── __init__.py
│   │       │   └── elasticity_model.py
│   │       ├── cancellation/        # Calibrated cancellation survival models
│   │       │   ├── __init__.py
│   │       │   └── cancellation_model.py
│   │       ├── scoring/             # Opportunity scoring & SHAP explainability
│   │       │   ├── __init__.py
│   │       │   └── opportunity_scorer.py
│   │       └── registry/            # MLflow experiment tracking & model registry
│   │           ├── __init__.py
│   │           └── mlflow_client.py
│   │
│   └── optimizer/                   # Mathematical Optimization Engine
│       └── src/inveniq_optimizer/
│           ├── __init__.py
│           ├── scenarios/           # Monte Carlo scenario generator & scenario reduction
│           │   ├── __init__.py
│           │   ├── generator.py
│           │   └── reduction.py
│           ├── engine/              # MILP + CVaR formulation using HiGHS / PuLP
│           │   ├── __init__.py
│           │   ├── formulator.py
│           │   └── solver.py
│           ├── postprocessing/      # Sensitivity analysis, shadow prices & frontier
│           │   ├── __init__.py
│           │   ├── frontier.py
│           │   └── sensitivity.py
│           └── backtest/            # Walk-forward backtester & stress testing
│               ├── __init__.py
│               ├── backtester.py
│               └── baselines.py
│
├── pipelines/                       # Data Ingestion, Synthetic Generation & Ingestion
│   └── src/inveniq_pipelines/
│       ├── __init__.py
│       ├── synthetic/               # Configurable, deterministic synthetic generator
│       │   ├── __init__.py
│       │   ├── generator.py
│       │   └── configs/
│       │       └── default_sim.yaml
│       ├── validation/              # Pandera / Pydantic schema validation contracts
│       │   ├── __init__.py
│       │   └── schemas.py
│       ├── censoring/               # Tobit & Look-to-book un-censoring module
│       │   ├── __init__.py
│       │   └── tobit_correction.py
│       └── ingestion/               # ETL runners to Parquet Lakehouse & PostgreSQL
│           ├── __init__.py
│           └── loader.py
│
├── web/                             # Next.js 14 Web Frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.mjs
│   └── src/
│       ├── app/                     # App router pages
│       │   ├── layout.tsx
│       │   ├── page.tsx             # Command Center
│       │   ├── recommendations/     # Ranked recommendations & drilldowns
│       │   ├── allocation/          # Sunburst & treemap budget views
│       │   ├── risk/                # CVaR distribution & efficient frontier
│       │   ├── simulator/           # What-if scenario stress-tester
│       │   ├── health/              # Model drift & data quality
│       │   └── approvals/           # Finance approval and audit logs
│       ├── components/              # Reusable UI components
│       │   ├── charts/              # Recharts & ECharts wrappers
│       │   ├── ui/                  # Buttons, modals, badges, sliders
│       │   └── layout/              # Navbar, sidebar, headers
│       └── lib/                     # API client, types, auth utilities
│           ├── api.ts
│           └── types.ts
│
└── tests/                           # Verification & Test Suites
    ├── unit/
    │   ├── test_schemas.py
    │   ├── test_synthetic_generator.py
    │   ├── test_censoring_correction.py
    │   ├── test_forecasting.py
    │   ├── test_elasticity.py
    │   ├── test_cancellation.py
    │   └── test_optimizer.py
    ├── integration/
    │   ├── test_pipeline_integration.py
    │   ├── test_api_endpoints.py
    │   └── test_worker_execution.py
    └── property/
        └── test_optimizer_invariants.py # Hypothesis property tests (budget <= B, q >= 0)
```

---

## 4. Architectural Decision Records (ADRs) Summary
- **ADR-001 (Monorepo):** Adopted modular monorepo with `inveniq_core` to enforce schema parity across pipelines, ML models, optimizer, and REST endpoints.
- **ADR-002 (Dual-Store Strategy):** PostgreSQL 16 for transactional state, approvals, and audit logs; DuckDB + partitioned Parquet for scalable analytical queries and feature store.
- **ADR-003 (Stochastic MILP + CVaR):** Mathematical optimization via Rockafellar-Uryasev linearized CVaR with scenario reduction to guarantee global optimality and strict risk bounds in $<60$ seconds.
- **ADR-004 (Quantile LightGBM & Conformal Prediction):** Probabilistic forecasting providing P10/P50/P90 distributions, calibrated with conformal bounds and reconciled across destination-product hierarchies.
- **ADR-005 (Tobit Censored Demand Recovery):** Un-censoring engine combining Tobit regression and search look-to-book multipliers to recover latent demand masked by sold-out capacity.
- **ADR-006 (Asynchronous Worker Model):** Asynchronous task execution using Celery/Redis with idempotency keys and distributed locking to safeguard against duplicate resource-intensive solves.
