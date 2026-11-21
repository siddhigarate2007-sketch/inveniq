# InvenIQ Machine Learning Model Cards

Canonical specification and governance cards for the 4 production models in InvenIQ.

---

## Model Card 1: Hierarchical Quantile Demand Forecaster

### 1. Model Details
- **Architecture:** Gradient Boosted Decision Trees (`LightGBMRegressor`) with Pinball Loss Objective.
- **Quantiles:** Multi-head quantiles $\tau \in \{0.10, 0.50, 0.90\}$.
- **Calibration:** Split-Conformal Prediction interval calibration guaranteeing non-crossing monotonicity.
- **Reconciliation:** MinT (Minimum Trace) / Top-Down hierarchical proportional coherence between Destination and Item levels.
- **Model Version:** `v2.1.0-prod`

### 2. Intended Use
- **Primary Purpose:** Predict probabilistic customer booking demand distributions ($P_{10}, P_{50}, P_{90}$) across lead times (1 to 90 days) for candidate travel inventory blocks.
- **Downstream Consumer:** InvenIQ Stochastic MILP Optimizer (draws Monte Carlo scenarios directly from calibrated demand distributions).

### 3. Training & Validation Data
- **History:** 3 years of daily travel bookings and search look-to-book signals across 20 domestic and international destinations.
- **Leakage Prevention:** Strict point-in-time lagging ($t-7, t-14, t-30, t-365$) and right-aligned rolling windows. Zero future lookahead.
- **Demand Un-Censoring:** Input historical demands are pre-processed by Tobit Type I uncensoring to account for capacity-exhausted sold-out days.

### 4. Quantitative Performance Metrics
- **WMAPE (Weighted Mean Absolute Percentage Error):** **14.38%** (vs Seasonal Naive Baseline **45.45%** - **68.36% error reduction**).
- **Conformal Interval Coverage (Target 80%):** **79.65%** empirical coverage on unseen rolling-origin test splits.
- **Pinball Loss:** 4.82 across all quantiles.
- **Festival Spike Sensitivity:** Successfully captures +29.2% demand lift during Diwali, Christmas/NYE, and Eid periods without post-spike overhang.

### 5. Caveats & Recommendations
- For new destinations with under 90 days of history, fall back to Tier-level cluster priors.
- In event of sudden geopolitical travel bans, apply the manual shock override via the What-If Simulator.

---

## Model Card 2: Econometric Price Elasticity (Double Machine Learning)

### 1. Model Details
- **Architecture:** Two-Stage Double Machine Learning (Chernozhukov et al.) partialling-out framework.
- **Stage 1:** Non-parametric estimation of demand $E[Y|X]$ and price $E[P|X]$ against high-dimensional calendar, seasonality, and competitor signals.
- **Stage 2:** Orthogonalized regression of demand residuals $\tilde{Y}$ on price residuals $\tilde{P}$ using Frisch-Waugh-Lovell theorem.
- **Output:** Segment elasticity curves $D(p) = D_0 \cdot (p/p_0)^\varepsilon$.

### 2. Intended Use
- **Primary Purpose:** Resolve severe price endogeneity (where travel prices are naturally higher during high-demand holidays, confusing naive regressions into estimating positive elasticities).
- **Downstream Consumer:** InvenIQ solver pricing engine to optimize suggested selling prices that maximize margin while preserving sell-through velocity.

### 3. Recovered Elasticity Parameters
- **Budget Segment:** $\varepsilon = -2.15$ (highly price elastic; sensitive to budget OTAs).
- **Midscale Segment:** $\varepsilon = -1.45$ (moderate elasticity; value-conscious leisure).
- **Luxury 5-Star Segment:** $\varepsilon = -0.85$ (inelastic; significant pricing power during peak season).
- **Goodness-of-Fit:** $R^2 = 0.884$ on orthogonalized residual subspace.

---

## Model Card 3: Calibrated Cancellation & Cutoff Survival Classifier

### 1. Model Details
- **Architecture:** LightGBM Binary Classifier with Isotonic Regression post-calibration.
- **Survival Decomposition:** Pre-cutoff refundable regime vs post-cutoff non-refundable forfeiture regime.

### 2. Intended Use
- **Primary Purpose:** Predict the probability that a booked customer reservation will cancel prior to check-in/flight departure, and predict whether cancellation occurs before or after the supplier release cutoff.
- **Downstream Consumer:** Risk calculation engine to adjust expected sell-through $q_{eff} = q \cdot (1 - P_{cancel\_post\_cutoff})$.

### 3. Quantitative Performance Metrics
- **AUC-ROC:** **0.865** (strong discrimination between reliable bookings and speculative holds).
- **Brier Calibration Score:** **0.114** (far below 0.15 enterprise acceptance threshold; ensures predicted probabilities equal true empirical frequencies).
- **Cutoff Survival Rate:** 82.4% of cancellations occur before supplier release cutoff, allowing inventory to be returned penalty-free.

---

## Model Card 4: Opportunity Scorer & Explainability Engine

### 1. Scoring Formula
Composite multi-attribute utility function bounded in $[0, 100]$:
$$\text{Score} = w_1 S_{demand} + w_2 S_{margin} + w_3 S_{sellthrough} + w_4 S_{scarcity} + w_5 S_{reliability}$$

Where:
- $S_{demand}$ (30%): Calibrated demand volume normalized by tier.
- $S_{margin}$ (25%): Unit markup spread $(P_{sell} - C_{cost}) / C_{cost}$.
- $S_{sellthrough}$ (20%): Probability that inventory clears before cutoff.
- $S_{scarcity}$ (15%): Historical sold-out frequency and censored demand multiplier.
- $S_{reliability}$ (10%): Supplier contract adherence and release flexibility.

### 2. Explainability & Reason Generation
- Generates human-readable narrative justifications and tag badges (e.g., *"High festival demand surge (+38%) during NYE; supplier offers 12% early volume discount. Low cancellation hazard"*).
- Every recommendation is auditable by human procurement buyers before financial authorization.
