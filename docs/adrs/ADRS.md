# Architecture Decision Records (ADRs) - InvenIQ

## ADR-001: Monorepo Architecture with Decoupled Services
- **Status:** Accepted
- **Context:** InvenIQ comprises an API service, an ML forecasting pipeline, a mathematical optimization engine, data pipelines, and a modern web dashboard. We must ensure cohesive shared data schemas (Pydantic v2 domain models) between data ingestion, ML models, optimization engines, and the API, while keeping deployment modular.
- **Decision:** Adopt a single monorepo structured into `/services`, `/pipelines`, `/web`, `/infra`, `/docs`, and `/tests`. Python components share core schemas through an internal package (`inveniq_core`), avoiding code duplication while maintaining strict interface contracts.
- **Consequences:**
  - *Pros:* Single source of truth for domain models, atomic commits across services and pipelines, streamlined local development via a unified Makefile, consistent CI/CD validation.
  - *Cons:* Requires disciplined boundary management to prevent circular dependencies between `inveniq_ml` and `inveniq_optimizer`.
- **Alternatives Considered:** Multi-repo setup (rejected due to schema synchronization drift and heavy cross-repo overhead during initial delivery).

---

## ADR-002: Dual-Store Strategy (PostgreSQL for OLTP + DuckDB/Parquet Lakehouse for Analytics)
- **Status:** Accepted
- **Context:** InvenIQ handles two distinct data access patterns: (1) transactional reads/writes for user authentication, optimization runs, scenario approvals, and audit trails; (2) columnar OLAP queries over millions of historical bookings, search queries, and multi-dimensional feature tables.
- **Decision:** Use PostgreSQL 16 for OLTP transactional data, configuration, user states, and approval audit logs. Use local DuckDB reading partitioned Parquet files (or S3/MinIO in production) as the embedded analytics engine and feature store.
- **Consequences:**
  - *Pros:* DuckDB provides zero-copy columnar scanning, vectorized SQL queries over Parquet at C++ speed without requiring a bulky Spark or Trino cluster. PostgreSQL provides ACID compliance for financial approvals and audit logs.
  - *Cons:* Ingestion pipelines must maintain synchronization between raw ingested Parquet files and entity catalogs in PostgreSQL.
- **Alternatives Considered:** PostgreSQL alone (too slow for multi-year search/booking aggregations), Spark/Delta Lake (over-engineered infrastructure footprint for single-node / medium-scale cluster deployments).

---

## ADR-003: Stochastic MILP with Rockafellar-Uryasev CVaR Linearization
- **Status:** Accepted
- **Context:** B2B travel inventory commitment involves high financial risk: unsold rooms/seats perish at departure, while stock-outs result in lost revenue and margin. Decisions must maximize expected profit while strictly limiting catastrophic downside losses under severe demand shocks.
- **Decision:** Formulate the inventory allocation as a Mixed-Integer Linear Program (MILP) incorporating Conditional Value-at-Risk (CVaR at confidence level $\alpha$) linearized using the Rockafellar-Uryasev variational formulation. We use HiGHS / CBC via PuLP/OR-Tools, augmented by Fast-Forward Scenario Reduction to compress 1,000 Monte Carlo forecast scenarios to $K=100$ representative scenarios.
- **Consequences:**
  - *Pros:* Exact mathematical optimality guarantee within user-defined solver tolerance (e.g. 1% MIP gap); linear formulation guarantees solvability in <60 seconds for 500 inventory items; rigorous financial risk control via CVaR; produces shadow prices for budget expansion.
  - *Cons:* MILP assumes linear or piecewise-linear elasticity and costs; non-linear dynamic pricing is handled sequentially or via piecewise discretization.
- **Alternatives Considered:** Pure Reinforcement Learning / Deep RL (black-box, no hard budget/allotment guarantee, unexplainable to Finance heads), Heuristic Greedy Allocation (sub-optimal, fails under complex multi-supplier allotment constraints).

---

## ADR-004: Quantile LightGBM with Conformal Prediction & Hierarchical Reconciliation
- **Status:** Accepted
- **Context:** Procurement requires probabilistic demand distributions (P10, P50, P90) across multiple aggregation levels (destination > product > hotel/flight > departure date). Over-forecasting creates unsold inventory waste; under-forecasting misses volume discounts.
- **Decision:** Deploy LightGBM Quantile Regression as the primary global forecasting model, trained with pinball loss at $\tau \in \{0.10, 0.50, 0.90\}$. Apply Conformal Prediction to guarantee valid finite-sample coverage on rolling-origin splits. Reconcile hierarchical levels using Minimum Trace (MinT) or Top-Down proportional allocation to ensure aggregate coherence.
- **Consequences:**
  - *Pros:* High inference speed, handles heterogeneous tabular signals (lead times, competitor indices, holiday lags), provides calibrated probability bounds required for stochastic scenario sampling.
  - *Cons:* Requires retraining when structural shifts occur; addressed via automated drift monitoring (Evidently).
- **Alternatives Considered:** ARIMA/Prophet alone (unable to scale across tens of thousands of entity-date series with multi-variable external signals), Temporal Fusion Transformer (TFT) (higher computational cost with negligible accuracy gains on tabular travel series).

---

## ADR-005: Tobit & Look-to-Book Un-censoring Engine for Sold-Out Periods
- **Status:** Accepted
- **Context:** When a hotel room block or flight allocation sells out, recorded booking count drops to zero or caps at allotment. Naive demand forecasting treats this capped observation as true demand, systematically under-predicting demand during peak festival and holiday spikes (censored data problem).
- **Decision:** Implement a dual un-censoring module: (1) Tobit regression (censored regression with right-censoring threshold at supplier allotment limit); (2) Search-to-booking multiplier: for sold-out days, estimate latent demand as $\hat{D} = \text{Searches} \times \overline{\text{Look-to-Book}}_{\text{uncensored}}$.
- **Consequences:**
  - *Pros:* Eliminates structural negative bias during peak travel dates, ensuring the optimizer pre-buys sufficient allotment for high-demand dates.
  - *Cons:* Search logs must be properly filtered for bots/scrapers to prevent artificially inflating demand estimates.
- **Alternatives Considered:** Ignore sold-outs (catastrophic under-buying during peak season), simple heuristic bump (+20%) (uncalibrated, causes over-allocation during non-elastic sold-outs).

---

## ADR-006: Asynchronous Job Processing with Redis, Distributed Locks, and Idempotency Keys
- **Status:** Accepted
- **Context:** Optimization runs and scenario backtests can take 10 to 60 seconds. HTTP clients must not hold open synchronous connections that time out on load balancers, and duplicate form submissions must not trigger redundant expensive MILP solves.
- **Decision:** Implement an asynchronous job pattern using Celery/RQ with Redis. API returns `202 Accepted` with a `job_id` and an idempotency key header check. Distributed locks via Redis prevent concurrent solves for the same scope. Run states and progress are tracked in PostgreSQL and polled via REST or streamed via Server-Sent Events (SSE).
- **Consequences:**
  - *Pros:* Resilient against network drops, horizontal scaling of solver workers independent of API gateway, safe retry semantics.
  - *Cons:* Frontend requires polling or SSE hooks to update progress state.
- **Alternatives Considered:** Synchronous blocking API calls (rejected: breaks p95 latency SLO and triggers HTTP 504 timeouts).
