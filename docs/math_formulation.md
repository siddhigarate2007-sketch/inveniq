# Mathematical Formulation: InvenIQ Optimization Engine & Demand Un-censoring

## 1. Mathematical Notation and Sets

### Sets and Indices
- $i \in \mathcal{I} = \{1, \dots, N\}$: Set of inventory candidate items (specific hotel-room category or flight route for a target travel date $T_i$).
- $s \in \mathcal{S}$: Set of certified suppliers offering inventory blocks.
- $d \in \mathcal{D}$: Set of geographic destinations (e.g., Goa, Dubai, Bangkok, Kashmir).
- $k \in \mathcal{K} = \{1, \dots, K\}$: Set of Monte Carlo demand scenarios, each occurring with probability $\pi_k$ (where $\sum_{k=1}^K \pi_k = 1$; for uniform draws $\pi_k = 1/K$).
- $t \in \mathcal{T}_i$: Candidate purchase timing options for item $i$ (e.g., $t_0 = \text{Buy Now}$, $t_1 = \text{Buy at } D-30$).

### Parameters
- $c_{i,s,t}$: Unit acquisition cost of item $i$ from supplier $s$ at timing option $t$ (₹).
- $p_i$: Suggested selling price for item $i$ to travel agents (₹).
- $D_{i,k}$: Realized un-censored customer demand for item $i$ in scenario $k$ (units).
- $r_i$: Net cancellation probability for item $i$ ($r_i \in [0, 1)$).
- $s_i$: Salvage recovery price per unsold unit if returned prior to release cutoff or liquidated ($s_i < c_{i,s,t}$).
- $p^{\text{pen}}_i$: Penalty cost per unsold unit past release cutoff (often $c_{i,s,t} - s_i$ or full loss).
- $B$: Total available procurement budget cap (₹).
- $\text{CAP}_d$: Maximum allowable budget exposure in destination $d$ ($\% \text{ of } B$).
- $\text{CAP}_s$: Maximum allowable budget exposure to supplier $s$ ($\% \text{ of } B$).
- $A_{i,s}$: Maximum allotment block available from supplier $s$ for item $i$.
- $\text{MOQ}_{i,s}$: Minimum order quantity required if purchasing item $i$ from supplier $s$.
- $\alpha$: CVaR risk confidence level (e.g., $\alpha = 0.95$ represents the worst $5\%$ of outcomes).
- $\lambda$: Risk-aversion penalty weight ($\lambda \ge 0$, mapped from user risk appetite: Conservative $\lambda=1.5$, Balanced $\lambda=0.7$, Aggressive $\lambda=0.1$).

---

## 2. Decision Variables

- $q_{i,s,t} \ge 0$: Integer decision variable representing the quantity of inventory item $i$ pre-bought from supplier $s$ at timing $t$.
  - Total quantity procured for item $i$: $Q_i = \sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}_i} q_{i,s,t}$.
- $z_{i,s,t} \in \{0, 1\}$: Binary decision variable indicating whether supplier $s$ is engaged for item $i$ at timing $t$ (enforces MOQ).
- $y_{i,k} \ge 0$: Actual units of item $i$ sold to travel agents under scenario $k$.
- $u_{i,k} \ge 0$: Unsold expired/salvaged units of item $i$ under scenario $k$.
- $\text{VaR}_\alpha$: Value-at-Risk threshold variable at confidence level $\alpha$.
- $v_k \ge 0$: Auxiliary shortfall variable measuring loss beyond $\text{VaR}_\alpha$ under scenario $k$.

---

## 3. Stochastic Profit & CVaR Formulation

### Scenario-Specific Realized Profit
For each scenario $k \in \mathcal{K}$, realized effective demand after cancellation adjustments is:
$$\tilde{D}_{i,k} = (1 - r_i) \cdot D_{i,k}$$

The units sold cannot exceed the available procured quantity $Q_i$ nor the effective demand $\tilde{D}_{i,k}$:
$$y_{i,k} \le Q_i \quad \forall i, k$$
$$y_{i,k} \le \tilde{D}_{i,k} \quad \forall i, k$$

The unsold units are:
$$u_{i,k} = Q_i - y_{i,k} \quad \forall i, k$$

The net financial profit $\Pi_k$ under scenario $k$ is given by:
$$\Pi_k = \sum_{i \in \mathcal{I}} \left[ p_i y_{i,k} + s_i u_{i,k} \right] - \sum_{i \in \mathcal{I}} \sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}_i} c_{i,s,t} q_{i,s,t}$$

The expected profit across all scenarios is:
$$\mathbb{E}[\Pi] = \sum_{k=1}^K \pi_k \Pi_k$$

### Rockafellar-Uryasev CVaR Linearization
Let the financial loss under scenario $k$ be $L_k = -\Pi_k$.  
Conditional Value-at-Risk at confidence level $\alpha$ represents the expected loss in the worst $(1-\alpha)$ fraction of outcomes:
$$\text{CVaR}_\alpha(L) = \min_{\zeta \in \mathbb{R}} \left\{ \zeta + \frac{1}{1 - \alpha} \sum_{k=1}^K \pi_k [L_k - \zeta]^+ \right\}$$

Introducing auxiliary surplus variables $v_k \ge 0$ where $v_k \ge L_k - \zeta = -\Pi_k - \zeta$:
$$\text{CVaR}_\alpha = \zeta + \frac{1}{1 - \alpha} \sum_{k=1}^K \pi_k v_k$$
Subject to:
$$v_k \ge -\Pi_k - \zeta \quad \forall k \in \{1, \dots, K\}$$
$$v_k \ge 0 \quad \forall k \in \{1, \dots, K\}$$
where $\zeta \in \mathbb{R}$ is the decision variable representing $\text{VaR}_\alpha$.

---

## 4. Complete Mixed-Integer Linear Program (MILP)

$$\max_{q, z, y, u, \zeta, v} \quad \mathbb{E}[\Pi] - \lambda \cdot \text{CVaR}_\alpha$$

Subject to:

1. **Total Budget Constraint:**
   $$\sum_{i \in \mathcal{I}} \sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}_i} c_{i,s,t} q_{i,s,t} \le B$$

2. **Supplier Allotment Cap & Minimum Order Quantity (MOQ):**
   $$\text{MOQ}_{i,s} \cdot z_{i,s,t} \le q_{i,s,t} \le A_{i,s} \cdot z_{i,s,t} \quad \forall i \in \mathcal{I}, s \in \mathcal{S}, t \in \mathcal{T}_i$$
   $$z_{i,s,t} \in \{0, 1\}$$

3. **Destination Risk Exposure Cap:**
   $$\sum_{i \in \mathcal{I}_d} \sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}_i} c_{i,s,t} q_{i,s,t} \le \text{CAP}_d \cdot B \quad \forall d \in \mathcal{D}$$

4. **Supplier Concentration Risk Exposure Cap:**
   $$\sum_{i \in \mathcal{I}} \sum_{t \in \mathcal{T}_i} c_{i,s,t} q_{i,s,t} \le \text{CAP}_s \cdot B \quad \forall s \in \mathcal{S}$$

5. **Effective Sales and Conservation Constraints:**
   $$y_{i,k} \le \sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}_i} q_{i,s,t} \quad \forall i, k$$
   $$y_{i,k} \le \tilde{D}_{i,k} \quad \forall i, k$$
   $$u_{i,k} = \sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}_i} q_{i,s,t} - y_{i,k} \quad \forall i, k$$

6. **CVaR Shortfall Bounds:**
   $$v_k \ge -\Pi_k - \zeta \quad \forall k \in \{1, \dots, K\}$$
   $$v_k \ge 0 \quad \forall k \in \{1, \dots, K\}$$

7. **Integrality and Non-Negativity:**
   $$q_{i,s,t} \in \mathbb{Z}_{\ge 0}, \quad z_{i,s,t} \in \{0, 1\}, \quad y_{i,k} \ge 0, \quad u_{i,k} \ge 0, \quad v_k \ge 0, \quad \zeta \in \mathbb{R}$$

---

## 5. Censored Demand Correction: Tobit & Look-to-Book Formulation

### The Censoring Problem
Let $D_t^*$ denote the true unobserved market demand for inventory item $i$ on date $t$, and let $C_t$ denote the supplier allotment capacity. The observed bookings $Y_t$ are right-censored:
$$Y_t = \min(D_t^*, C_t)$$

If $Y_t < C_t$, demand was fully observed ($Y_t = D_t^*$).  
If $Y_t = C_t$, demand was censored ($D_t^* \ge C_t$).

### Type I Right-Censored Tobit Model
We specify the latent demand model as:
$$D_t^* = \mathbf{x}_t^\top \boldsymbol{\beta} + \epsilon_t, \quad \epsilon_t \sim \mathcal{N}(0, \sigma^2)$$

The log-likelihood function across uncensored ($I_0$) and censored ($I_1$) observations is:
$$\ln L(\boldsymbol{\beta}, \sigma) = \sum_{t \in I_0} \left[ -\frac{1}{2} \ln(2\pi\sigma^2) - \frac{(Y_t - \mathbf{x}_t^\top \boldsymbol{\beta})^2}{2\sigma^2} \right] + \sum_{t \in I_1} \ln\left( 1 - \Phi\left( \frac{C_t - \mathbf{x}_t^\top \boldsymbol{\beta}}{\sigma} \right) \right)$$
where $\Phi(\cdot)$ is the standard normal cumulative distribution function.

### Search Look-to-Book Uplift Estimator
For sold-out days where search signals are present:
$$\hat{D}_t^* = \max\left( Y_t, \quad \text{Searches}_t \times \widehat{\text{L2B}}_{\text{baseline}}(t) \right)$$
where $\widehat{\text{L2B}}_{\text{baseline}}(t)$ is the median look-to-book ratio on non-sold-out days for the same destination, day of week, and lead time. This estimator provides an empirical un-censored benchmark that feeds directly into the feature store.
