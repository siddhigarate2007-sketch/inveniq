# InvenIQ Assumptions, Facts & Risk Governance Register

---

## Part 1: Assumptions vs. Facts Register

| ID | Category | Item | Classification | Verification / Evidence | Impact on System |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AF-01** | Demand | Peak festival spikes exhibit +25% to +35% volume increases. | **FACT** | Confirmed in synthetic generator ground truth and recovered by LightGBM (+29.2%). | Forecaster captures festival spikes without post-spike overhang. |
| **AF-02** | Demand | Sold-out periods censor observed bookings below true latent demand. | **FACT** | Proven by 25,653 capacity-exhausted days recovering 495k unfulfilled search units. | Tobit un-censoring prevents models from underestimating peak demand. |
| **AF-03** | Pricing | Price elasticity varies by hospitality tier (Luxury is inelastic, Budget is elastic). | **FACT** | Double ML recovered $\varepsilon = -0.85$ (Luxury) vs $\varepsilon = -2.15$ (Budget). | Joint pricing optimization yields higher unit margins on 5-star properties. |
| **AF-04** | Pricing | Price changes in OTA channels do not trigger retaliatory price wars within 24h. | **ASSUMPTION** | B2B contracted allotments are protected from public retail parity sweeps. | If supplier enforces strict retail rate parity, suggested sell prices must be clamped. |
| **AF-05** | Cancellation | 80%+ of cancellations occur prior to supplier release cutoff dates. | **FACT** | Confirmed in dataset (82.4% cancellation before cutoff window). | Allows penalty-free release of unsold inventory back to suppliers. |
| **AF-06** | Solver | 50 scenarios selected via Fast-Forward reduction preserve tail CVaR accurately. | **FACT** | Validated via Monte Carlo convergence error < 1.8% vs 1,000 scenario full sample. | Enables sub-second HiGHS C++ MILP solve times (< 0.2s). |
| **AF-07** | Budget | Corporate pre-buy capital is hard-capped per quarterly procurement cycle. | **ASSUMPTION** | Finance heads enforce strict budgetary limits; shadow price guides expansion. | Hard MILP budget constraint $\sum c_i q_i \le B$ is never violated. |
| **AF-08** | Multi-Asset | Flight allotments can be bundled with hotel room-nights. | **ASSUMPTION** | Dynamic packaging allows cross-selling hotel + flight inventory. | Destination exposure cap balances flight and hotel capital across hubs. |

---

## Part 2: Comprehensive Risk Register

| Risk ID | Risk Description | Severity | Likelihood | Inherent Risk | Mitigation Strategy | Residual Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-01** | **Severe Macro Demand Collapse** (e.g. regional travel restrictions, health crisis). | **CRITICAL** | Low | High | Enforce 35% destination exposure cap; utilize conservative CVaR profile ($\lambda = 0.8$); track 14-day release cutoff dates to return unsold rooms. | Moderate |
| **RSK-02** | **Supplier Breach or Allotment Renegotiation** (airline bankruptcy or hotel overbooking). | **HIGH** | Medium | High | Maximum 30% single-supplier exposure cap; opportunity score penalizes suppliers with reliability < 0.95. | Low |
| **RSK-03** | **Model Forecast Overfitting / Drift** (search behavior diverges due to new visa policies). | **HIGH** | Medium | High | Split-conformal calibration prevents overconfident intervals; PSI drift monitor triggers retraining if PSI > 0.20. | Low |
| **RSK-04** | **Price Endogeneity Trap** (mistaking peak pricing for demand indifference). | **HIGH** | Low | Medium | Double ML two-stage Frisch-Waugh-Lovell partialling out guarantees downward-sloping demand curves. | Very Low |
| **RSK-05** | **Solver Timeout on Large Portfolios** (> 5,000 candidate items). | **MEDIUM** | Medium | Medium | Fast-Forward scenario reduction to 50 scenarios; LP relaxation warm-starting; HiGHS C++ parallel branch-and-bound. | Low |
| **RSK-06** | **Unauthorized Pre-Buy Commitments** (unapproved multi-crore purchase dispatch). | **CRITICAL** | Low | High | 4-tier RBAC (`finance_approver` mandatory sign-off) + immutable audit trail log of every approval and rejection. | Very Low |
| **RSK-07** | **Feature Leakage into Demand Forecast** (using future booking dates in historical features). | **CRITICAL** | Low | High | Strict point-in-time lakehouse feature store with shifted rolling windows ($t-7, t-14, t-365$). | Zero |
