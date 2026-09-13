"""
A.R.G.U.S. — Authentication Service (OOP Application Layer)
Coordinates account registration, credential verification, JWT issuance, and audit tracking.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from database.models.user import User
from database.repository import create_user
from backend.security.password import hash_password, verify_password
from backend.security.jwt import create_access_token
from backend.config import settings
from backend.schemas.auth import UserRegisterRequest, TokenResponse
from .user_service import UserService
from .audit_service import AuditService


class AuthService:
    """
    Application service managing authentication workflows.
    Demonstrates OOP composition by delegating persistence to UserService and audit to AuditService.
    """

    def __init__(self, db: Session, user_service: UserService, audit_service: AuditService):
        self.db = db
        self.user_service = user_service
        self.audit_service = audit_service

    def register(self, request: UserRegisterRequest, client_ip: str = "127.0.0.1") -> User:
        """
        Registers a new user account with a uniquely salted bcrypt password hash.

        Raises
        ------
        HTTPException (409)
            If the username or email is already taken.
        """
        # 1. Uniqueness validation
        if self.user_service.get_by_username(request.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{request.username}' is already registered.",
            )

        if self.user_service.get_by_email(request.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{request.email}' is already registered.",
            )

        # 2. Ensure role exists
        role_name = request.role or "USER"
        role = self.user_service.ensure_role(role_name)

        # 3. Hash password with bcrypt
        hashed_pw = hash_password(request.password)

        # 4. Create user in database
        user = create_user(
            session=self.db,
            username=request.username,
            email=request.email,
            hashed_password=hashed_pw,
            role_id=role.role_id,
        )

        # 5. Record structured audit event
        self.audit_service.log_event(
            event_type="AUTH_USER_REGISTERED",
            action="CREATE_ACCOUNT",
            resource_type="user",
            actor_id=user.username,
            actor_type="USER",
            resource_id=str(user.user_id),
            details={"email": user.email, "role": role.name, "client_ip": client_ip},
        )

        return user

    def authenticate(self, username: str, password: str, client_ip: str = "127.0.0.1") -> TokenResponse:
        """
        Authenticates credentials and issues a signed stateless JWT.

        Raises
        ------
        HTTPException (401)
            If authentication fails.
        """
        user = self.user_service.get_by_username(username)
        if user is None or not user.is_active:
            self.audit_service.log_login_failure(
                username=username,
                client_ip=client_ip,
                reason="User not found or inactive",
            )
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Constant-time password verification
        if not verify_password(password, user.hashed_password):
            self.audit_service.log_login_failure(
                username=username,
                client_ip=client_ip,
                reason="Invalid credentials",
            )
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Success: issue JWT
        token_claims = {
            "sub": user.username,
            "user_id": str(user.user_id),
            "role": user.role.name if user.role else "USER",
        }
        access_token = create_access_token(token_claims)

        self.audit_service.log_login_success(
            username=user.username,
            user_id=str(user.user_id),
            client_ip=client_ip,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            user_id=user.user_id,
            username=user.username,
            role=user.role.name if user.role else "USER",
        )
