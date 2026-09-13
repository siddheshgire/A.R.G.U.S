"""
A.R.G.U.S. — API Routes Package
"""

from .health import router as health_router
from .transactions import router as transactions_router
from .auth import router as auth_router
from .admin import router as admin_router
from .iot import iot_router
from .analytics import router as analytics_router
from .alerts import router as alerts_router
from .devices import router as devices_router

__all__ = [
    "health_router",
    "transactions_router",
    "auth_router",
    "admin_router",
    "iot_router",
    "analytics_router",
    "alerts_router",
    "devices_router",
]
