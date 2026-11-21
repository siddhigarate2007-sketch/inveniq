"""Inventory catalog and opportunity candidate endpoints."""

from typing import Any
from fastapi import APIRouter, Depends, Query
from inveniq_api.auth.rbac import get_current_user
from inveniq_core.db_store import db_store
from inveniq_core.schemas.user import User
from inveniq_ml.scoring.opportunity_scorer import OpportunityScorer

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/destinations")
async def list_destinations(current_user: User = Depends(get_current_user)) -> list[dict[str, Any]]:
    """Lists destination catalog with tier, domestic status, and region."""
    return [
        {"destination_id": "DEST_GOA", "name": "Goa", "region": "West India", "tier": 2, "domestic": True},
        {"destination_id": "DEST_DUBAI", "name": "Dubai", "region": "Middle East", "tier": 1, "domestic": False},
        {"destination_id": "DEST_KASHMIR", "name": "Kashmir", "region": "North India", "tier": 2, "domestic": True},
        {"destination_id": "DEST_BANGKOK", "name": "Bangkok", "region": "Southeast Asia", "tier": 1, "domestic": False},
        {"destination_id": "DEST_SINGAPORE", "name": "Singapore", "region": "Southeast Asia", "tier": 1, "domestic": False},
        {"destination_id": "DEST_KERALA", "name": "Kerala", "region": "South India", "tier": 2, "domestic": True},
        {"destination_id": "DEST_JAIPUR", "name": "Jaipur", "region": "North India", "tier": 2, "domestic": True},
        {"destination_id": "DEST_BALI", "name": "Bali", "region": "Southeast Asia", "tier": 2, "domestic": False},
    ]


@router.get("/candidates")
async def list_opportunity_candidates(
    destination_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Returns candidate inventory blocks enriched with 5-pillar Opportunity Scores."""
    candidates = db_store.load_candidates_for_optimization()
    if destination_id:
        candidates = candidates[candidates["destination_id"] == destination_id]

    scorer = OpportunityScorer()
    df_scored = scorer.score_all_candidates(candidates)
    return df_scored.to_dict(orient="records")
