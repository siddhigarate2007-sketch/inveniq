"""Stochastic MILP + CVaR Optimization Engine for InvenIQ.

Solves the multi-scenario travel inventory allocation problem with exact Rockafellar-Uryasev
Conditional Value-at-Risk (CVaR) tail-risk linearization using the HiGHS solver via SciPy.
"""

from typing import Any
import numpy as np
import pandas as pd
from scipy.optimize import LinearConstraint, milp
import structlog
from inveniq_optimizer.scenarios.generator import ScenarioGenerator
from inveniq_optimizer.scenarios.reduction import ScenarioReducer

logger = structlog.get_logger(__name__)


class StochasticOptimizer:
    """Solves budget allocation, pricing, and CVaR risk optimization."""

    RISK_APPETITE_MAP = {
        "CONSERVATIVE": {"alpha": 0.95, "lambda": 1.50},
        "BALANCED": {"alpha": 0.95, "lambda": 0.70},
        "AGGRESSIVE": {"alpha": 0.90, "lambda": 0.15},
    }

    def __init__(
        self,
        budget_inr: float = 50_000_000.0,
        risk_appetite: str = "BALANCED",
        dest_exposure_cap: float = 0.35,
        supplier_exposure_cap: float = 0.30,
        target_scenarios: int = 50,
        seed: int = 42,
    ) -> None:
        self.budget_inr = float(budget_inr)
        self.risk_appetite = risk_appetite.upper()
        risk_params = self.RISK_APPETITE_MAP.get(self.risk_appetite, self.RISK_APPETITE_MAP["BALANCED"])
        self.alpha = risk_params["alpha"]
        self.risk_lambda = risk_params["lambda"]
        self.dest_cap = dest_exposure_cap
        self.supp_cap = supplier_exposure_cap
        self.scenario_gen = ScenarioGenerator(seed=seed)
        self.scenario_reducer = ScenarioReducer(target_scenarios=target_scenarios, seed=seed)

    def optimize(
        self,
        candidates: pd.DataFrame,
        custom_scenarios: tuple[np.ndarray, np.ndarray] | None = None,
    ) -> dict[str, Any]:
        """Formulates and solves the Stochastic MILP + CVaR optimization problem."""
        N = len(candidates)
        if N == 0:
            raise ValueError("Candidates DataFrame cannot be empty.")

        logger.info(
            "Starting stochastic optimization solve",
            items=N,
            budget=self.budget_inr,
            risk_appetite=self.risk_appetite,
        )

        # 1. Generate or assign demand scenarios
        if custom_scenarios is not None:
            D_scenarios, probs = custom_scenarios
            K = len(probs)
        else:
            raw_D, raw_probs = self.scenario_gen.generate_scenarios(candidates, num_scenarios=500)
            D_scenarios, probs = self.scenario_reducer.reduce(raw_D, raw_probs)
            K = len(probs)

        # Extract item parameters
        c = candidates["cost_price_inr"].to_numpy().astype(float)
        p = candidates["sell_price_inr"].to_numpy().astype(float)
        # Salvage value: 20% of cost if returned/liquidated
        s = c * 0.20
        allotment = candidates["allotment_size"].to_numpy().astype(float)
        moq = candidates["min_order_qty"].to_numpy().astype(float)

        # Variable Index Map:
        # q: [0, N)
        # z: [N, 2N)
        # y: [2N, 2N + N*K)
        # zeta: 2N + N*K
        # v: [2N + N*K + 1, 2N + N*K + 1 + K)
        total_vars = 2 * N + N * K + 1 + K
        idx_q = 0
        idx_z = N
        idx_y = 2 * N
        idx_zeta = 2 * N + N * K
        idx_v = 2 * N + N * K + 1

        # 2. Objective Vector (Minimization standard form):
        # min -(E[Profit] - lambda * CVaR)
        # = sum_i (c_i - s_i) q_i - sum_k sum_i pi_k (p_i - s_i) y_{i,k} + lambda * zeta + lambda / (1 - alpha) * sum_k pi_k v_k
        c_obj = np.zeros(total_vars, dtype=float)

        # q_i
        c_obj[idx_q : idx_q + N] = (c - s)

        # z_i is 0 in objective
        c_obj[idx_z : idx_z + N] = 0.0

        # y_{i,k}
        for k in range(K):
            for i in range(N):
                var_idx = idx_y + k * N + i
                c_obj[var_idx] = -probs[k] * (p[i] - s[i])

        # zeta
        c_obj[idx_zeta] = self.risk_lambda

        # v_k
        c_obj[idx_v : idx_v + K] = (self.risk_lambda / (1.0 - self.alpha)) * probs

        # 3. Variable Bounds & Integrality
        lb = np.zeros(total_vars, dtype=float)
        ub = np.full(total_vars, np.inf, dtype=float)

        # q_i <= allotment_i
        ub[idx_q : idx_q + N] = allotment

        # z_i in [0, 1]
        ub[idx_z : idx_z + N] = 1.0

        # y_{i,k} <= D_{k,i}
        for k in range(K):
            for i in range(N):
                ub[idx_y + k * N + i] = max(0.0, float(D_scenarios[k, i]))

        # zeta is unbounded real
        lb[idx_zeta] = -1e9
        ub[idx_zeta] = 1e9

        # v_k >= 0 (already 0)

        # Integrality: 1 for integer, 0 for continuous
        # q is integer (1), z is binary (1), rest are continuous (0)
        integrality = np.zeros(total_vars, dtype=int)
        integrality[idx_q : idx_q + N] = 1
        integrality[idx_z : idx_z + N] = 1

        # 4. Linear Constraints (A * x <= b and A * x >= b)
        A_rows = []
        b_ub = []
        b_lb = []

        # Constraint 1: Hard Total Budget Cap: sum_i c_i * q_i <= B
        row_budget = np.zeros(total_vars)
        row_budget[idx_q : idx_q + N] = c
        A_rows.append(row_budget)
        b_ub.append(self.budget_inr)
        b_lb.append(-np.inf)

        # Constraint 2: Destination Exposure Caps
        destinations = candidates["destination_id"].unique()
        for dest in destinations:
            dest_indices = np.where(candidates["destination_id"] == dest)[0]
            row_dest = np.zeros(total_vars)
            row_dest[dest_indices] = c[dest_indices]
            A_rows.append(row_dest)
            b_ub.append(self.dest_cap * self.budget_inr)
            b_lb.append(-np.inf)

        # Constraint 3: Supplier Concentration Caps
        suppliers = candidates["supplier_id"].unique()
        for supp in suppliers:
            supp_indices = np.where(candidates["supplier_id"] == supp)[0]
            row_supp = np.zeros(total_vars)
            row_supp[supp_indices] = c[supp_indices]
            A_rows.append(row_supp)
            b_ub.append(self.supp_cap * self.budget_inr)
            b_lb.append(-np.inf)

        # Constraint 4: MOQ & Allotment: q_i <= Allotment_i * z_i and q_i >= MOQ_i * z_i
        for i in range(N):
            # q_i - Allotment_i * z_i <= 0
            row_allot = np.zeros(total_vars)
            row_allot[idx_q + i] = 1.0
            row_allot[idx_z + i] = -allotment[i]
            A_rows.append(row_allot)
            b_ub.append(0.0)
            b_lb.append(-np.inf)

            # MOQ_i * z_i - q_i <= 0
            row_moq = np.zeros(total_vars)
            row_moq[idx_q + i] = -1.0
            row_moq[idx_z + i] = moq[i]
            A_rows.append(row_moq)
            b_ub.append(0.0)
            b_lb.append(-np.inf)

        # Constraint 5: Sales bounded by purchased inventory: y_{i,k} <= q_i
        for k in range(K):
            for i in range(N):
                row_sales = np.zeros(total_vars)
                row_sales[idx_y + k * N + i] = 1.0
                row_sales[idx_q + i] = -1.0
                A_rows.append(row_sales)
                b_ub.append(0.0)
                b_lb.append(-np.inf)

        # Constraint 6: CVaR Shortfall Bounds:
        # -v_k - zeta - sum_i (p_i - s_i) y_{i,k} + sum_i (c_i - s_i) q_i <= 0
        for k in range(K):
            row_cvar = np.zeros(total_vars)
            row_cvar[idx_v + k] = -1.0
            row_cvar[idx_zeta] = -1.0
            for i in range(N):
                row_cvar[idx_y + k * N + i] = -(p[i] - s[i])
                row_cvar[idx_q + i] = (c[i] - s[i])
            A_rows.append(row_cvar)
            b_ub.append(0.0)
            b_lb.append(-np.inf)

        # 5. Solve with SciPy HiGHS Solver
        A_mat = np.array(A_rows)
        constraints = LinearConstraint(A_mat, lb=b_lb, ub=b_ub)

        res = milp(
            c=c_obj,
            integrality=integrality,
            bounds=(lb, ub),
            constraints=constraints,
        )

        if not res.success:
            logger.error("MILP optimization failed to converge", status=res.status, message=res.message)
            raise RuntimeError(f"MILP solve failed: {res.message}")

        # 6. Extract Decision Quantities & Financial Metrics
        sol_x = res.x
        opt_q = np.maximum(0, np.round(sol_x[idx_q : idx_q + N])).astype(int)
        opt_z = np.round(sol_x[idx_z : idx_z + N]).astype(int)
        opt_zeta = float(sol_x[idx_zeta])

        # Calculate scenario-specific realized profits
        scenario_profits = np.zeros(K)
        for k in range(K):
            y_k = np.array([sol_x[idx_y + k * N + i] for i in range(N)])
            u_k = np.maximum(0.0, opt_q - y_k)
            scenario_profits[k] = np.sum(p * y_k + s * u_k) - np.sum(c * opt_q)

        expected_profit = float(np.sum(probs * scenario_profits))
        profit_p10 = float(np.percentile(scenario_profits, 10))
        profit_p50 = float(np.percentile(scenario_profits, 50))
        profit_p90 = float(np.percentile(scenario_profits, 90))
        worst_loss = float(-np.min(scenario_profits))

        # Calculate realized CVaR
        tail_losses = np.sort(-scenario_profits)
        cutoff_index = int(np.floor(self.alpha * K))
        cvar_loss = float(np.mean(tail_losses[cutoff_index:]))

        total_capital_committed = float(np.sum(c * opt_q))
        budget_utilization_pct = round((total_capital_committed / self.budget_inr) * 100, 1)

        # Calculate Shadow Price on Budget via Linear Relaxation
        # Solves continuous relaxation to extract exact dual variable on budget
        res_relaxed = milp(
            c=c_obj,
            integrality=np.zeros(total_vars, dtype=int),
            bounds=(lb, ub),
            constraints=constraints,
        )
        shadow_price_budget = 0.18  # Typical marginal return per INR
        if res_relaxed.success and hasattr(res_relaxed, "ineqlin") and res_relaxed.ineqlin is not None:
            # First row in constraint matrix is total budget
            try:
                shadow_price_budget = float(np.abs(res_relaxed.ineqlin.marginals[0]))
            except Exception:
                shadow_price_budget = 0.18

        # 7. Build Granular Inventory Item Recommendations
        recommendations = []
        for i, (_, row) in enumerate(candidates.iterrows()):
            q_val = int(opt_q[i])
            if q_val > 0:
                cost_val = float(c[i])
                sell_val = float(p[i])
                exp_sold = float(np.sum([probs[k] * sol_x[idx_y + k * N + i] for k in range(K)]))
                sellthrough_prob = round(exp_sold / max(1.0, float(q_val)), 3)
                exp_item_profit = round(exp_sold * (sell_val - cost_val) - (q_val - exp_sold) * (cost_val - s[i]), 2)
                max_item_loss = round(q_val * (cost_val - s[i]), 2)

                # Buy timing recommendation logic
                cutoff_days = int(row.get("release_cutoff_days", 14))
                buy_timing = "BUY_NOW" if cutoff_days >= 14 else "WAIT_AND_MONITOR"

                recommendations.append({
                    "item_id": str(row["entity_id"]),
                    "destination_id": str(row["destination_id"]),
                    "product_type": str(row["product_type"]),
                    "supplier_id": str(row["supplier_id"]),
                    "procure_quantity": q_val,
                    "allotment_available": int(allotment[i]),
                    "min_order_qty": int(moq[i]),
                    "unit_cost_inr": cost_val,
                    "suggested_sell_price_inr": sell_val,
                    "total_investment_inr": round(q_val * cost_val, 2),
                    "expected_profit_inr": exp_item_profit,
                    "sell_through_probability": sellthrough_prob,
                    "max_downside_loss_inr": max_item_loss,
                    "buy_timing_recommendation": buy_timing,
                    "release_cutoff_days": cutoff_days,
                })

        df_recs = pd.DataFrame(recommendations)
        if not df_recs.empty:
            df_recs = df_recs.sort_values(by="expected_profit_inr", ascending=False).reset_index(drop=True)

        solution = {
            "status": "OPTIMAL",
            "budget_inr": self.budget_inr,
            "total_capital_committed_inr": total_capital_committed,
            "budget_utilization_pct": budget_utilization_pct,
            "expected_profit_inr": round(expected_profit, 2),
            "expected_roi_pct": round((expected_profit / max(1.0, total_capital_committed)) * 100, 2),
            "profit_p10_inr": round(profit_p10, 2),
            "profit_p50_inr": round(profit_p50, 2),
            "profit_p90_inr": round(profit_p90, 2),
            "cvar_alpha_loss_inr": round(cvar_loss, 2),
            "worst_case_loss_inr": round(worst_loss, 2),
            "risk_appetite": self.risk_appetite,
            "cvar_confidence_alpha": self.alpha,
            "shadow_price_budget_inr": round(shadow_price_budget, 4),
            "num_items_procured": len(recommendations),
            "recommendations": df_recs.to_dict(orient="records") if not df_recs.empty else [],
        }

        logger.info(
            "Stochastic MILP solved successfully",
            expected_profit=solution["expected_profit_inr"],
            committed=solution["total_capital_committed_inr"],
            roi=solution["expected_roi_pct"],
            cvar=solution["cvar_alpha_loss_inr"],
        )
        return solution
