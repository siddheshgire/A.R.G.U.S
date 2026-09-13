"""
A.R.G.U.S. — Authentication & Authorization FastAPI Dependencies
Provides token extraction, identity resolution, and service injection.
"""

import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database.models.user import User
from backend.dependencies.database import get_db
from backend.security.jwt import decode_access_token
from backend.services.user_service import UserService
from backend.services.audit_service import AuditService
from backend.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db=db)


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    return AuditService(db=db)


def get_auth_service(
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> AuthService:
    return AuthService(db=db, user_service=user_service, audit_service=audit_service)


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Resolves the authenticated user if a valid bearer token is present.
    Returns None if no token is provided or if the token is invalid/expired.
    """
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if not username:
            return None
        user_service = UserService(db=db)
        user = user_service.get_by_username(username)
        if user and user.is_active:
            return user
    except HTTPException:
        return None
    return None


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Enforces authentication requirement on protected endpoints.
    Raises HTTP 401 if missing, invalid, or expired.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required to access this resource.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_service = UserService(db=db)
    user = user_service.get_by_username(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user record no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended or deactivated.",
        )
    return user
