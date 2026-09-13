"""
A.R.G.U.S. — Dependencies Package
"""

from .database import get_db
from .models import get_model_manager, get_transaction_service
from .auth import (
    get_user_service,
    get_audit_service,
    get_auth_service,
    get_optional_current_user,
    get_current_user,
)
from .iot import get_authenticated_device

__all__ = [
    "get_db",
    "get_model_manager",
    "get_transaction_service",
    "get_user_service",
    "get_audit_service",
    "get_auth_service",
    "get_optional_current_user",
    "get_current_user",
    "get_authenticated_device",
]
