"""Opportunity Scoring & Explainability Engine for InvenIQ.

Ranks candidate travel inventory on a 0-100 scale using a multi-factor decision model:
1. Demand Forecast Momentum (30%)
2. Profit Margin Percentage (25%)
3. Calibrated Sell-Through Probability (20%)
4. Historical Sold-Out Scarcity Signal (15%)
5. Supplier Reliability & Release Cutoff Buffer (10%)

Provides granular pillar attributions, standardized reason codes, and human-readable narratives.
"""

from typing import Any
import numpy as np
import pandas as pd
from scipy.stats import norm
import structlog

logger = structlog.get_logger(__name__)


class OpportunityScorer:
    """Computes explainable composite opportunity scores for travel inventory candidates."""

    WEIGHTS = {
        "demand": 0.30,
        "margin": 0.25,
        "sell_through": 0.20,
        "sold_out": 0.15,
        "supplier": 0.10,
    }

    @staticmethod
    def calculate_sell_through_probability(
        forecast_p10: float,
        forecast_p50: float,
        forecast_p90: float,
        allotment: float,
    ) -> float:
        """Estimates probability that demand meets or exceeds 80% of allotment capacity."""
        target_qty = 0.80 * allotment
        # Estimate standard deviation from 80% prediction interval [P10, P90]
        # P90 - P10 approx 2.56 * sigma
        sigma = max(1.0, (forecast_p90 - forecast_p10) / 2.563)
        mu = forecast_p50

        # P(Demand >= target_qty) = 1 - Phi((target_qty - mu) / sigma)
        z = (target_qty - mu) / sigma
        prob = float(1.0 - norm.cdf(z))
        return float(np.clip(prob, 0.05, 0.99))

    def score_item(
        self,
        item_id: str,
        forecast_p10: float,
        forecast_p50: float,
        forecast_p90: float,
        cost_price: float,
        sell_price: float,
        allotment: int,
        supplier_reliability: float,
        release_cutoff_days: int,
        historical_soldout_rate: float = 0.20,
        cancel_prob: float = 0.08,
        is_festival: bool = False,
    ) -> dict[str, Any]:
        """Calculates 0-100 opportunity score, component attributions, and reason codes."""
        # 1. Demand score (0-100)
        demand_ratio = forecast_p50 / max(1.0, float(allotment))
        s_demand = min(100.0, demand_ratio * 100.0)

        # 2. Margin score (0-100)
        margin_pct = (sell_price - cost_price) / max(1.0, sell_price)
        # 30% margin corresponds to score 100
        s_margin = min(100.0, max(0.0, (margin_pct / 0.30) * 100.0))

        # 3. Sell-through probability score (0-100)
        p_sellthrough = self.calculate_sell_through_probability(
            forecast_p10, forecast_p50, forecast_p90, allotment
        )
        s_sellthrough = p_sellthrough * 100.0

        # 4. Sold-out scarcity score (0-100)
        s_soldout = min(100.0, historical_soldout_rate * 250.0)

        # 5. Supplier reliability & cutoff buffer score (0-100)
        cutoff_buffer_norm = min(1.0, release_cutoff_days / 30.0)
        s_supplier = (supplier_reliability * 0.7 + cutoff_buffer_norm * 0.3) * 100.0

        # Composite weighted score
        composite_score = (
            self.WEIGHTS["demand"] * s_demand
            + self.WEIGHTS["margin"] * s_margin
            + self.WEIGHTS["sell_through"] * s_sellthrough
            + self.WEIGHTS["sold_out"] * s_soldout
            + self.WEIGHTS["supplier"] * s_supplier
        )

        # Apply cancellation penalty discount if high
        if cancel_prob > 0.12:
            composite_score *= 0.90

        final_score = round(float(np.clip(composite_score, 0.0, 100.0)), 1)

        # Generate Reason Codes & Explanations
        reason_codes = []
        if margin_pct >= 0.22:
            reason_codes.append("HIGH_MARGIN_EXPANSION")
        if p_sellthrough >= 0.85:
            reason_codes.append("HIGH_SELLTHROUGH_CONFIDENCE")
        if is_festival or demand_ratio >= 1.2:
            reason_codes.append("PEAK_DEMAND_SURGE")
        if historical_soldout_rate >= 0.30:
            reason_codes.append("SCARCITY_HIGH_SOLDOUT_HISTORY")
        if supplier_reliability >= 0.95 and release_cutoff_days >= 21:
            reason_codes.append("RELIABLE_SUPPLIER_SAFE_CUTOFF")

        # Warning codes
        warning_codes = []
        if cancel_prob > 0.12:
            warning_codes.append("HIGH_CANCELLATION_RISK")
        if release_cutoff_days <= 7:
            warning_codes.append("TIGHT_RELEASE_CUTOFF")

        # Construct Human-Readable Reason Narrative
        narrative_parts = []
        if "HIGH_MARGIN_EXPANSION" in reason_codes:
            narrative_parts.append(f"High gross margin ({round(margin_pct * 100, 1)}%)")
        if "HIGH_SELLTHROUGH_CONFIDENCE" in reason_codes:
            narrative_parts.append(f"strong sell-through confidence ({round(p_sellthrough * 100, 1)}%)")
        if "PEAK_DEMAND_SURGE" in reason_codes:
            narrative_parts.append("peak seasonal demand momentum")
        if "RELIABLE_SUPPLIER_SAFE_CUTOFF" in reason_codes:
            narrative_parts.append(f"partner reliability ({round(supplier_reliability * 100, 1)}%) with {release_cutoff_days}d cutoff window")

        if not narrative_parts:
            narrative_parts.append("Balanced risk-return travel inventory candidate")

        reason_string = "Recommended: " + ", ".join(narrative_parts) + "."
        if warning_codes:
            reason_string += f" Caution: {', '.join(warning_codes)}."

        return {
            "entity_id": item_id,
            "opportunity_score": final_score,
            "grade": "Tier-A" if final_score >= 80 else ("Tier-B" if final_score >= 60 else "Tier-C"),
            "margin_pct": round(margin_pct * 100, 1),
            "sell_through_probability": round(p_sellthrough, 3),
            "pillar_contributions": {
                "demand": round(self.WEIGHTS["demand"] * s_demand, 1),
                "margin": round(self.WEIGHTS["margin"] * s_margin, 1),
                "sell_through": round(self.WEIGHTS["sell_through"] * s_sellthrough, 1),
                "scarcity": round(self.WEIGHTS["sold_out"] * s_soldout, 1),
                "supplier": round(self.WEIGHTS["supplier"] * s_supplier, 1),
            },
            "reason_codes": reason_codes,
            "warning_codes": warning_codes,
            "reason_string": reason_string,
        }

    def score_all_candidates(
        self,
        df_candidates: pd.DataFrame,
    ) -> pd.DataFrame:
        """Batch scores all candidate inventory items and returns ranked dataframe."""
        results = []
        for _, row in df_candidates.iterrows():
            item_score = self.score_item(
                item_id=str(row["entity_id"]),
                forecast_p10=float(row.get("q_10", 15.0)),
                forecast_p50=float(row.get("q_50", 30.0)),
                forecast_p90=float(row.get("q_90", 50.0)),
                cost_price=float(row.get("cost_price_inr", 5000.0)),
                sell_price=float(row.get("sell_price_inr", 6500.0)),
                allotment=int(row.get("allotment_size", 40)),
                supplier_reliability=float(row.get("reliability_score", 0.92)),
                release_cutoff_days=int(row.get("release_cutoff_days", 14)),
                historical_soldout_rate=float(row.get("soldout_rate", 0.20)),
                cancel_prob=float(row.get("cancel_prob", 0.08)),
                is_festival=bool(row.get("is_festival", False)),
            )
            results.append(item_score)

        df_scored = pd.DataFrame(results).sort_values(by="opportunity_score", ascending=False).reset_index(drop=True)
        return df_scored
