"""FastAPI Application Entry Point for InvenIQ."""

import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from inveniq_api.monitoring.metrics import metrics_collector
from inveniq_api.routers import (
    audit_router,
    auth_router,
    health_router,
    inventory_router,
    optimization_router,
    risk_router,
)
from inveniq_core.config import settings
from inveniq_core.logging import configure_logging

configure_logging(settings.LOG_LEVEL)
logger = structlog.get_logger(__name__)

app = FastAPI(
    title="InvenIQ API",
    description="Production-grade AI-Powered Travel Inventory Optimization & Risk Engine for TBO.com",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Measures latency and logs all incoming requests in structured JSON."""
    start_time = time.time()
    response = await call_next(request)
    duration_s = time.time() - start_time
    duration_ms = round(duration_s * 1000, 2)

    metrics_collector.record_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=duration_s,
    )

    logger.info(
        "HTTP Request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response


# Register Routers under /api/v1
app.include_router(auth_router, prefix="/api/v1")
app.include_router(optimization_router, prefix="/api/v1")
app.include_router(risk_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")


@app.get("/metrics", tags=["Monitoring"])
async def metrics_endpoint():
    """Returns application metrics formatted for Prometheus scraping."""
    return Response(
        content=metrics_collector.export_prometheus_text(),
        media_type="text/plain; version=0.0.4",
    )


@app.get("/")
async def root():
    return {
        "service": "InvenIQ API",
        "version": "1.0.0",
        "status": "OPERATIONAL",
        "docs": "/docs",
    }
