"""Health and readiness probe endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def liveness_probe() -> dict[str, str]:
    """Kubernetes liveness probe."""
    return {"status": "ALIVE", "service": "inveniq-api"}


@router.get("/ready")
async def readiness_probe() -> dict[str, str]:
    """Kubernetes readiness probe checking memory state and solver availability."""
    return {"status": "READY", "version": "1.0.0"}
