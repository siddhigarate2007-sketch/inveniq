"""Core Pydantic v2 domain schemas."""

from inveniq_core.schemas.entities import (
    BookingRecord,
    CalendarDay,
    Destination,
    ExternalSignals,
    FlightRoute,
    HotelProperty,
    SearchRecord,
    SoldOutRecord,
    Supplier,
    SupplierTerms,
)
from inveniq_core.schemas.optimization import (
    ApprovalActionRequest,
    OptimizationRunRequest,
    OptimizationRunResponse,
    RecommendationItem,
    RunStatus,
    StressTestRequest,
)
from inveniq_core.schemas.user import (
    AuditLogEntry,
    LoginRequest,
    Token,
    TokenData,
    User,
    UserInDB,
    UserRole,
)

__all__ = [
    "Destination",
    "HotelProperty",
    "FlightRoute",
    "Supplier",
    "CalendarDay",
    "BookingRecord",
    "SearchRecord",
    "SoldOutRecord",
    "SupplierTerms",
    "ExternalSignals",
    "UserRole",
    "User",
    "UserInDB",
    "LoginRequest",
    "Token",
    "TokenData",
    "AuditLogEntry",
    "RunStatus",
    "OptimizationRunRequest",
    "OptimizationRunResponse",
    "RecommendationItem",
    "ApprovalActionRequest",
    "StressTestRequest",
]
