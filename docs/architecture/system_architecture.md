# InvenIQ: System Architecture Documentation (C4 Specification)

## 1. System Context Diagram (C4 Level 1)
InvenIQ sits at the center of TBO.com's procurement, pricing, and risk management operations. It connects internal decision-makers with upstream supplier terms, downstream core booking distribution, and external market signals.

```mermaid
flowchart TD
    subgraph Users ["User Personas"]
        Buyer["Procurement / Buying Manager"]
        Analyst["Revenue / Pricing Analyst"]
        SupplierMgr["Supplier Relations Manager"]
        FinanceHead["Finance & Risk Head (Approver)"]
    end

    subgraph CoreSystem ["InvenIQ Platform"]
        InvenIQ["InvenIQ Platform<br/>(AI-Powered Travel Inventory Optimization & Risk Engine)"]
    end

    subgraph ExternalSystems ["External & Upstream/Downstream Systems"]
        TBO_Core["TBO Core Booking Engine<br/>(Transactions, Bookings, Searches)"]
        Suppliers["Suppliers & GDS / Wholesalers<br/>(Hotels, Airlines, Bedbanks)"]
        MarketFeeds["External Market Intelligence<br/>(Events, Holidays, FX, Fuel, Competitor Rates)"]
        ERP["Corporate ERP & Financial Ledger<br/>(Budget Disbursement & Accounts Payable)"]
    end

    Buyer -->|"Configures budget, targets, covenants"| InvenIQ
    Analyst -->|"Inspects demand, elasticity, opportunity scores"| InvenIQ
    SupplierMgr -->|"Manages allotments, contracts, cutoffs"| InvenIQ
    FinanceHead -->|"Reviews CVaR exposure, approves/rejects buys"| InvenIQ

    TBO_Core -->|"Historical bookings, searches, sold-out telemetry"| InvenIQ
    Suppliers -->|"Contract rates, release deadlines, penalties"| InvenIQ
    MarketFeeds -->|"Holidays, weather, competitor index, macro trends"| InvenIQ

    InvenIQ -->|"Approved inventory commitment purchase orders"| ERP
    InvenIQ -->|"Optimal selling prices & allocation blocks"| TBO_Core
```

---

## 2. Container Diagram (C4 Level 2)
The container architecture implements a high-throughput, decoupled micro-service and pipeline topology.

```mermaid
flowchart TB
    subgraph ClientTier ["Presentation Layer"]
        WebUI["Next.js 14 Web Frontend<br/>(React, TypeScript, Tailwind, Recharts/ECharts)"]
    end

    subgraph IngressTier ["Gateway & Security"]
        ReverseProxy["Reverse Proxy / Nginx Gateway<br/>(SSL Termination, Rate Limiting, CORS)"]
    end

    subgraph ApplicationTier ["Application & Worker Services"]
        API["FastAPI Application Server<br/>(Async REST API, Auth JWT, OpenAPI)"]
        CeleryWorker["Celery / Async Task Workers<br/>(Optimization Solver, ML Ingestion, Simulation)"]
        CeleryBeat["Celery Beat Scheduler<br/>(Periodic Forecasts & Drift Checks)"]
    end

    subgraph DataTier ["Data & Storage Layer"]
        Postgres[("PostgreSQL 16 OLTP<br/>(Entities, Users, Recommendations, Audit Logs, Scenarios)")]
        RedisCache[("Redis 7<br/>(Task Queue, Session Store, Distributed Locks, Result Cache)")]
        DuckLake[("DuckDB & Parquet Lakehouse<br/>(Historical Bookings, Searches, Feature Store)")]
        ObjectStore[("MinIO / S3 Object Storage<br/>(MLflow Model Registry, Forecast Artifacts, Raw Dumps)")]
    end

    subgraph ObservabilityTier ["Observability & Monitoring"]
        Prometheus["Prometheus Metric Collector"]
        Grafana["Grafana Dashboards"]
        EvidentlyService["Evidently Drift Monitor"]
    end

    WebUI -->|"HTTPS / REST / WebSocket"| ReverseProxy
    ReverseProxy -->|"HTTP / ASGI"| API
    API -->|"Read / Write State & Audits"| Postgres
    API -->|"Submit async jobs & get status"| RedisCache
    API -->|"Query analytical aggregates"| DuckLake
    API -->|"Emit metrics"| Prometheus

    CeleryWorker -->|"Fetch queued jobs & cache state"| RedisCache
    CeleryWorker -->|"Read features & training data"| DuckLake
    CeleryWorker -->|"Read / Write models & artifacts"| ObjectStore
    CeleryWorker -->|"Persist optimization runs & decisions"| Postgres
    CeleryWorker -->|"Track runs & register models"| ObjectStore
    CeleryBeat -->|"Trigger scheduled workflows"| RedisCache

    EvidentlyService -->|"Read inference logs & baseline"| DuckLake
    EvidentlyService -->|"Publish drift alerts"| Prometheus
    Prometheus -->|"Scrape metrics"| API
    Prometheus -->|"Scrape metrics"| CeleryWorker
    Grafana -->|"Visualize metrics"| Prometheus
```

---

## 3. Component Diagrams (C4 Level 3)

### 3.1 Data & Ingestion Pipeline Component Diagram
```mermaid
flowchart LR
    subgraph IngestionPipelines ["Data Pipeline & Quality Layer"]
        Adapter["Source Adapters<br/>(TBO Core, Synthetic Generator, External APIs)"]
        Validator["Schema Validation Engine<br/>(Pandera / Pydantic Contracts)"]
        CensoringEngine["Tobit / Look-to-Book<br/>Demand Un-censoring Module"]
        FeatureEngine["Point-in-Time Feature Store<br/>(Lag, Rolling, Seasonality, Kalendar)"]
        LakehouseWriter["Idempotent Parquet Lakehouse Writer"]
    end

    Adapter -->|"Raw ingestion streams"| Validator
    Validator -->|"Validated clean records"| CensoringEngine
    CensoringEngine -->|"Un-censored latent demand"| FeatureEngine
    FeatureEngine -->|"Partitioned feature matrices"| LakehouseWriter
```

### 3.2 Machine Learning & Opportunity Scoring Component Diagram
```mermaid
flowchart TD
    subgraph MLSubsystem ["ML & Forecasting Subsystem"]
        DataExtractor["Lakehouse Feature Extractor"]
        LightGBMQuantile["Hierarchical LightGBM<br/>(P10, P50, P90 Quantiles)"]
        Reconciliation["Hierarchical Reconciliation<br/>(MinT / Top-Down Allocation)"]
        ConformalCalibrator["Conformal Predictor<br/>(Coverage Calibration)"]
        ElasticityModel["Double ML / Log-Log<br/>Price Elasticity Estimator"]
        CancellationModel["Calibrated Survival Classifier<br/>(Isotonic GBM: P(Cancel|LeadTime))"]
        OpportunityScorer["Opportunity Scoring Engine<br/>(Explainable Multi-factor SHAP)"]
        ModelRegistry["MLflow Model Registry"]
    end

    DataExtractor --> LightGBMQuantile
    LightGBMQuantile --> Reconciliation
    Reconciliation --> ConformalCalibrator
    DataExtractor --> ElasticityModel
    DataExtractor --> CancellationModel

    ConformalCalibrator --> OpportunityScorer
    ElasticityModel --> OpportunityScorer
    CancellationModel --> OpportunityScorer

    OpportunityScorer -->|"Score, Reason Codes, Elasticity, Forecast"| ModelRegistry
```

### 3.3 Stochastic Optimization & Risk Engine Component Diagram
```mermaid
flowchart TD
    subgraph OptimizerSubsystem ["Stochastic Optimization & Risk Engine"]
        ScenarioGenerator["Monte Carlo Scenario Engine<br/>(Draws from Calibrated Demand Distributions)"]
        ScenarioReducer["Scenario Reduction Module<br/>(Fast Forward Selection / K-Means Clustering)"]
        MILPFormulator["MILP + CVaR Model Builder<br/>(Rockafellar-Uryasev Linearization)"]
        ConstraintEnforcer["Constraint Manager<br/>(Budget, Supplier Allotment, Exposure, Cutoffs)"]
        SolverAdapter["High-Performance Solver Adapter<br/>(HiGHS / OR-Tools / CBC)"]
        PostOptimizer["Sensitivity, Shadow Price &<br/>Efficient Frontier Extractor"]
    end

    ScenarioGenerator -->|"N=1,000 Scenarios"| ScenarioReducer
    ScenarioReducer -->|"Reduced K=100 Representative Scenarios"| MILPFormulator
    ConstraintEnforcer --> MILPFormulator
    MILPFormulator --> SolverAdapter
    SolverAdapter -->|"Optimal Decision Vectors (q_i, p_i, buy_date)"| PostOptimizer
```

---

## 4. End-to-End Sequence Diagram
Demonstrates how a Procurement Manager triggers an optimization run, how the async pipeline computes the decision, how risk checks are applied, and how the Finance Head approves the purchase commitment.

```mermaid
sequenceDiagram
    autonumber
    actor Buyer as Procurement Manager
    actor Finance as Finance / Risk Head
    participant Web as Web Frontend (Next.js)
    participant API as FastAPI Gateway
    participant Redis as Redis Queue / Cache
    participant Worker as Celery Worker
    participant ML as ML & Feature Engine
    participant Opt as Stochastic Optimizer (MILP+CVaR)
    participant DB as PostgreSQL DB
    participant ERP as TBO Core / ERP

    Buyer->>Web: Configure Run (Budget: ₹5 Cr, Risk: Balanced, Caps)
    Web->>API: POST /api/v1/optimization/runs (with Idempotency-Key)
    API->>DB: Record Run State (Status = PENDING)
    API->>Redis: Enqueue Job (run_id, params)
    API-->>Web: 202 Accepted (run_id, status: PENDING)

    Worker->>Redis: Dequeue Job (run_id)
    Worker->>DB: Update Run State (Status = IN_PROGRESS)
    Worker->>ML: Fetch Calibrated Forecasts, Elasticity & Cancellation Curves
    ML-->>Worker: Quantiles (P10/P50/P90), E[Demand], Elasticity, Cancel Probabilities
    Worker->>Opt: Build Stochastic Scenarios & Solve MILP + CVaR
    Opt-->>Worker: Solution (Optimal q_i, p_i, Timing, E[Profit], CVaR, Shadow Prices)
    Worker->>DB: Persist Recommendations, Frontier & Explainability Metrics
    Worker->>DB: Update Run State (Status = COMPLETED_AWAITING_APPROVAL)
    Worker->>Redis: Publish Run Finished Event

    Web->>API: GET /api/v1/optimization/runs/{id} (Poll / SSE)
    API-->>Web: Run Completed, Recommendations & Risk Frontier Available
    Buyer->>Web: Review Recommendations, Sunburst & Efficient Frontier
    Buyer->>Web: Submit for Financial Review

    Finance->>Web: Inspect CVaR Downside, Worst-Case Scenarios & Sensitivity
    Finance->>Web: Click "Approve Purchase Commitment"
    Web->>API: POST /api/v1/optimization/runs/{id}/approve (JWT Auth)
    API->>DB: Record Audit Log (Approver, Timestamp, Rationale)
    API->>DB: Transition Run State (Status = APPROVED)
    API->>ERP: Dispatch Purchase Commitment Orders & Dynamic Price Rules
    ERP-->>API: 200 OK (Orders Acknowledged)
    API-->>Web: Approval Confirmed & Dispatched
```
