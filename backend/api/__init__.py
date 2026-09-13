"""
A.R.G.U.S. — API Router Aggregation
"""

from fastapi import APIRouter
from backend.api.routes import (
    health_router,
    transactions_router,
    auth_router,
    admin_router,
    iot_router,
    analytics_router,
    alerts_router,
    devices_router,
)

api_router = APIRouter()

# Health endpoints mounted at root (/health, /ready)
api_router.include_router(health_router)

# Versioned API routes (/api/v1/...)
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(transactions_router)
v1_router.include_router(analytics_router)
v1_router.include_router(alerts_router)
v1_router.include_router(devices_router)
v1_router.include_router(admin_router)
v1_router.include_router(iot_router)

api_router.include_router(v1_router)

__all__ = ["api_router"]
