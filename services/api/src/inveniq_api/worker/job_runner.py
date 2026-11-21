"""Asynchronous optimization job execution worker for InvenIQ."""

import concurrent.futures
import uuid
from datetime import datetime
from typing import Any
import structlog
from inveniq_core.db_store import db_store
from inveniq_core.schemas.optimization import (
    OptimizationRunRequest,
    OptimizationRunResponse,
    RecommendationItem,
    RunStatus,
)
from inveniq_core.schemas.user import UserRole
from inveniq_api.monitoring.metrics import metrics_collector
from inveniq_ml.scoring.opportunity_scorer import OpportunityScorer
from inveniq_optimizer.engine.solver import StochasticOptimizer

logger = structlog.get_logger(__name__)

# Dedicated thread pool for long-running optimization solves
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def _execute_optimization_job(run_id: str) -> None:
    """Synchronous worker execution target executed inside background thread pool."""
    logger.info("Worker picked up optimization job", run_id=run_id)
    run = db_store.get_run(run_id)
    if not run:
        logger.error("Run not found in store", run_id=run_id)
        return

    # Update to IN_PROGRESS
    run.status = RunStatus.IN_PROGRESS
    run.updated_at = datetime.utcnow()
    db_store.save_run(run)

    try:
        # Load candidates
        candidates = db_store.load_candidates_for_optimization()

        # Initialize Stochastic Optimizer
        optimizer = StochasticOptimizer(
            budget_inr=run.budget_inr,
            risk_appetite=run.risk_appetite,
            dest_exposure_cap=0.40,
            supplier_exposure_cap=0.35,
            target_scenarios=30,
        )

        solution = optimizer.optimize(candidates)

        # Score items with Opportunity Scorer
        scorer = OpportunityScorer()
        recs_out = []
        for r in solution["recommendations"]:
            scored = scorer.score_item(
                item_id=r["item_id"],
                forecast_p10=r["procure_quantity"] * 0.7,
                forecast_p50=r["procure_quantity"] * 1.0,
                forecast_p90=r["procure_quantity"] * 1.4,
                cost_price=r["unit_cost_inr"],
                sell_price=r["suggested_sell_price_inr"],
                allotment=r["allotment_available"],
                supplier_reliability=0.96,
                release_cutoff_days=r["release_cutoff_days"],
            )

            rec_item = RecommendationItem(
                item_id=r["item_id"],
                destination_id=r["destination_id"],
                product_type=r["product_type"],
                supplier_id=r["supplier_id"],
                procure_quantity=r["procure_quantity"],
                allotment_available=r["allotment_available"],
                min_order_qty=r["min_order_qty"],
                unit_cost_inr=r["unit_cost_inr"],
                suggested_sell_price_inr=r["suggested_sell_price_inr"],
                total_investment_inr=r["total_investment_inr"],
                expected_profit_inr=r["expected_profit_inr"],
                sell_through_probability=r["sell_through_probability"],
                max_downside_loss_inr=r["max_downside_loss_inr"],
                buy_timing_recommendation=r["buy_timing_recommendation"],
                release_cutoff_days=r["release_cutoff_days"],
                opportunity_score=scored["opportunity_score"],
                reason_string=scored["reason_string"],
            )
            recs_out.append(rec_item)

        # Update run with solution
        run.status = RunStatus.COMPLETED_AWAITING_APPROVAL
        run.updated_at = datetime.utcnow()
        run.total_capital_committed_inr = solution["total_capital_committed_inr"]
        run.budget_utilization_pct = solution["budget_utilization_pct"]
        run.expected_profit_inr = solution["expected_profit_inr"]
        run.expected_roi_pct = solution["expected_roi_pct"]
        run.profit_p10_inr = solution["profit_p10_inr"]
        run.profit_p50_inr = solution["profit_p50_inr"]
        run.profit_p90_inr = solution["profit_p90_inr"]
        run.cvar_alpha_loss_inr = solution["cvar_alpha_loss_inr"]
        run.worst_case_loss_inr = solution["worst_case_loss_inr"]
        run.shadow_price_budget_inr = solution["shadow_price_budget_inr"]
        run.num_items_procured = solution["num_items_procured"]
        run.recommendations = recs_out

        db_store.save_run(run)
        metrics_collector.record_optimization_run(
            status=run.status.value,
            risk_appetite=run.risk_appetite,
            duration_seconds=0.5,
            budget_inr=run.budget_inr,
            profit_inr=run.expected_profit_inr or 0.0,
            cvar_inr=run.cvar_alpha_loss_inr or 0.0,
        )
        logger.info("Optimization job successfully completed", run_id=run_id, profit=run.expected_profit_inr)

    except Exception as e:
        logger.error("Optimization job failed", run_id=run_id, error=str(e), exc_info=True)
        run.status = RunStatus.FAILED
        run.updated_at = datetime.utcnow()
        run.error_message = str(e)
        db_store.save_run(run)


class JobRunner:
    """Dispatches asynchronous optimization jobs with idempotency key checks."""

    @staticmethod
    def dispatch_run(
        request: OptimizationRunRequest,
        user_id: str,
        user_email: str,
        idempotency_key: str | None = None,
        sync: bool = False,
    ) -> OptimizationRunResponse:
        """Dispatches an optimization job and returns initial pending response."""
        # Check idempotency
        if idempotency_key:
            existing = db_store.get_run_by_idempotency_key(idempotency_key)
            if existing:
                logger.info("Idempotent run matched, returning existing instance", key=idempotency_key, run_id=existing.run_id)
                return existing

        run_id = f"RUN_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"

        run_obj = OptimizationRunResponse(
            run_id=run_id,
            idempotency_key=idempotency_key,
            status=RunStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by_user_id=user_id,
            budget_inr=request.budget_inr,
            risk_appetite=request.risk_appetite,
        )

        db_store.save_run(run_obj)
        db_store.record_audit(
            user_id=user_id,
            user_email=user_email,
            user_role=UserRole.BUYER,
            action="SUBMIT_RUN",
            target_type="OPTIMIZATION_RUN",
            target_id=run_id,
            details={"budget_inr": request.budget_inr, "risk_appetite": request.risk_appetite},
        )

        if sync:
            _execute_optimization_job(run_id)
            return db_store.get_run(run_id) or run_obj

        _executor.submit(_execute_optimization_job, run_id)
        return run_obj
