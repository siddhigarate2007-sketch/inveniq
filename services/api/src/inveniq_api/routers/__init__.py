"""API router package."""

from inveniq_api.routers.audit import router as audit_router
from inveniq_api.routers.auth import router as auth_router
from inveniq_api.routers.health import router as health_router
from inveniq_api.routers.inventory import router as inventory_router
from inveniq_api.routers.optimization import router as optimization_router
from inveniq_api.routers.risk import router as risk_router

__all__ = [
    "auth_router",
    "optimization_router",
    "risk_router",
    "inventory_router",
    "audit_router",
    "health_router",
]
