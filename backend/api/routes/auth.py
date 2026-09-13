"""
A.R.G.U.S. — Authentication Endpoints
Provides registration, login credentials verification, JWT issuance, and profile query.
"""

from fastapi import APIRouter, Depends, Request, status

from backend.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
)
from backend.dependencies.auth import get_auth_service, get_current_user
from backend.services.auth_service import AuthService
from database.models.user import User

router = APIRouter(prefix="/auth", tags=["Identity & Access Management"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Account",
    description="Registers a new user account with a uniquely salted bcrypt password hash.",
)
def register_endpoint(
    request_data: UserRegisterRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    client_ip = http_request.client.host if http_request.client else "127.0.0.1"
    user = auth_service.register(request=request_data, client_ip=client_ip)
    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role.name if user.role else "USER",
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Authentication & Token Issuance",
    description="Authenticates credentials and issues a signed stateless HS256 JWT bearer token.",
)
def login_endpoint(
    credentials: UserLoginRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    client_ip = http_request.client.host if http_request.client else "127.0.0.1"
    return auth_service.authenticate(
        username=credentials.username,
        password=credentials.password,
        client_ip=client_ip,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns the profile attributes and authorization role of the authenticated caller.",
)
def get_me_endpoint(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.name if current_user.role else "USER",
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
