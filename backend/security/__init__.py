"""
A.R.G.U.S. — Security Architecture Package
"""

from .password import hash_password, verify_password, validate_password_strength
from .jwt import create_access_token, decode_access_token
from .rbac import UserRole, RoleChecker, require_role
from .middleware import SecurityHeadersMiddleware, RateLimitMiddleware, rate_limiter
from .device_auth import hash_device_key, verify_device_credentials, extract_device_credentials

__all__ = [
    "hash_password",
    "verify_password",
    "validate_password_strength",
    "create_access_token",
    "decode_access_token",
    "UserRole",
    "RoleChecker",
    "require_role",
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
    "rate_limiter",
    "hash_device_key",
    "verify_device_credentials",
    "extract_device_credentials",
]
