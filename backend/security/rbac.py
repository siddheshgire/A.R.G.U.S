"""
A.R.G.U.S. — Role-Based Access Control (RBAC)
Enforces endpoint authorization hierarchies (USER, ANALYST, ADMIN, AUDITOR).
"""

from enum import Enum
from typing import List, Tuple
from fastapi import HTTPException, status

from database.models.user import User


class UserRole(str, Enum):
    """Supported operational security roles."""
    USER = "USER"
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"


# Explicit Role Hierarchy: ADMIN has superset privileges over ANALYST and USER
ROLE_HIERARCHY = {
    UserRole.ADMIN: {UserRole.ADMIN, UserRole.ANALYST, UserRole.USER, UserRole.AUDITOR},
    UserRole.ANALYST: {UserRole.ANALYST, UserRole.USER},
    UserRole.AUDITOR: {UserRole.AUDITOR, UserRole.USER},
    UserRole.USER: {UserRole.USER},
}


class RoleChecker:
    """
    FastAPI dependency enforcing that the authenticated user possesses one of the required roles.
    """

    def __init__(self, allowed_roles: Tuple[str, ...]):
        self.allowed_roles = [r.upper() for r in allowed_roles]

    def __call__(self, current_user: User) -> User:
        user_role = current_user.role.name.upper() if current_user.role else UserRole.USER.value
        
        # Direct match or hierarchical authorization
        has_permission = False
        if user_role in self.allowed_roles:
            has_permission = True
        elif user_role == UserRole.ADMIN.value:
            has_permission = True
        elif user_role == UserRole.ANALYST.value and UserRole.USER.value in self.allowed_roles:
            has_permission = True

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: User with role '{user_role}' is not authorized to perform this operation.",
            )
        return current_user


def require_role(*roles: str):
    """Helper returning a RoleChecker dependency for the specified role names."""
    return RoleChecker(roles)
