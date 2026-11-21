# InvenIQ REST API Reference

Base URL: `http://localhost:8000/api/v1`  
Interactive Swagger Docs: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

---

## 1. Authentication & Security

All secure endpoints require a standard HTTP Authorization Bearer token header:
```http
Authorization: Bearer <jwt_access_token>
```

### `POST /api/v1/auth/login`
Authenticates user credentials and returns a signed JWT access token.

#### Request Body
```json
{
  "email": "buyer@tbo.com",
  "password": "InvenIQ2026!"
}
```

#### Response `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in_seconds": 86400,
  "user": {
    "user_id": "USR_BUYER_01",
    "email": "buyer@tbo.com",
    "full_name": "Rajesh Sharma",
    "role": "buyer",
    "is_active": true,
    "created_at": "2026-01-15T09:00:00Z"
  }
}
```

---

## 2. Optimization Endpoints

### `POST /api/v1/optimization/runs`
Dispatches an asynchronous inventory optimization job using the HiGHS C++ MILP engine.
- **RBAC Roles Allowed:** `buyer`, `analyst`, `admin`
- **Optional Header:** `X-Idempotency-Key` (guarantees safe duplicate execution)

#### Request Body
```json
{
  "budget_inr": 50000000.0,
  "risk_appetite": "BALANCED",
  "dest_exposure_cap": 0.35,
  "supplier_exposure_cap": 0.30,
  "notes": "Q4 Peak Season Pre-Buy Portfolio"
}
```

#### Response `202 Accepted`
```json
{
  "run_id": "RUN_20261120_001",
  "status": "COMPLETED_AWAITING_APPROVAL",
  "created_at": "2026-11-20T11:30:00Z",
  "budget_inr": 50000000.0,
  "risk_appetite": "BALANCED",
  "total_capital_committed_inr": 48625000.0,
  "budget_utilization_pct": 97.25,
  "expected_profit_inr": 9840000.0,
  "expected_roi_pct": 20.24,
  "cvar_alpha_loss_inr": 1420000.0,
  "worst_case_loss_inr": 2650000.0,
  "shadow_price_budget_inr": 0.185,
  "num_items_procured": 42,
  "recommendations": [...]
}
```

---

### `GET /api/v1/optimization/runs`
Lists historical optimization runs.
- **Parameters:** `limit` (default 50), `offset` (default 0)
- **RBAC Roles Allowed:** Any authenticated user.

---

### `GET /api/v1/optimization/runs/{run_id}`
Retrieves complete details and recommendation items for a specific optimization run.

---

### `POST /api/v1/optimization/runs/{run_id}/approve`
Approves or rejects capital commitments for an optimization run.
- **RBAC Roles Allowed:** `finance_approver`, `admin` ONLY.

#### Request Body
```json
{
  "approved": true,
  "notes": "Approved: Within Q4 board-authorized capital allocation ceiling."
}
```

#### Response `200 OK`
Returns updated `OptimizationRunResponse` with status `"APPROVED"` and approver audit notes.

---

## 3. Risk & Simulation Endpoints

### `GET /api/v1/risk/frontier`
Calculates Pareto-optimal Efficient Frontier points mapping Expected Profit against CVaR Risk.
- **Query Parameters:** `budget_inr` (float), `points` (int 3-10)

#### Response `200 OK`
```json
[
  {
    "risk_tolerance_lambda": 0.0,
    "expected_profit_inr": 10920000.0,
    "cvar_loss_inr": 3250000.0,
    "worst_case_loss_inr": 5800000.0,
    "roi_pct": 21.9
  },
  {
    "risk_tolerance_lambda": 0.5,
    "expected_profit_inr": 9840000.0,
    "cvar_loss_inr": 1420000.0,
    "worst_case_loss_inr": 2650000.0,
    "roi_pct": 20.24
  }
]
```

---

### `GET /api/v1/risk/sensitivity`
Computes budget sensitivity across multipliers `[0.7x, 0.85x, 1.0x, 1.15x, 1.3x]` and shadow prices ($\partial \Pi / \partial B$).

---

### `POST /api/v1/risk/stress-test`
Simulates portfolio solvency under demand collapse, cost inflation, and cancellation cascades.

#### Request Body
```json
{
  "demand_shock_pct": -20.0,
  "cost_inflation_pct": 10.0,
  "cancellation_surge_pct": 50.0
}
```

---

## 4. Inventory Endpoints

### `GET /api/v1/inventory/destinations`
Lists active destinations with regional and domestic tags.

### `GET /api/v1/inventory/candidates`
Returns inventory candidate blocks enriched with 5-pillar Opportunity Scores.

---

## 5. Governance & Health Endpoints

### `GET /api/v1/audit/logs`
Returns immutable audit trail of submissions, reviews, and financial authorizations.
- **RBAC Roles Allowed:** `finance_approver`, `analyst`, `admin`.

### `GET /metrics`
Prometheus standard exposition format containing API latency, throughput, HiGHS solver execution durations, and CVaR tail metrics.

### `GET /api/v1/health/live` & `GET /api/v1/health/ready`
Kubernetes liveness and readiness probe endpoints.
