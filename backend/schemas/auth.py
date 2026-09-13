"""
A.R.G.U.S. — Authentication & User Schemas
Pydantic contracts for user registration, credentials verification, and JWT responses.
"""

import re
import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict

from backend.security.password import validate_password_strength


class UserRegisterRequest(BaseModel):
    """Registration request payload for new accounts."""
    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., min_length=3, max_length=50, description="Unique account handle")
    email: str = Field(..., min_length=5, max_length=255, description="Valid email address")
    password: str = Field(..., min_length=8, max_length=128, description="Secure account password")
    role: Optional[str] = Field(default="USER", description="Initial role assignment (USER, ANALYST, ADMIN)")

    @field_validator("username")
    @classmethod
    def validate_username_format(cls, v: str) -> str:
        clean = v.strip()
        if not re.match(r"^[a-zA-Z0-9_\-]+$", clean):
            raise ValueError("Username may only contain letters, numbers, hyphens, and underscores.")
        return clean

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError("Invalid email format.")
        return clean

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        validate_password_strength(v)
        return v

    @field_validator("role")
    @classmethod
    def validate_role_name(cls, v: Optional[str]) -> str:
        if v is None:
            return "USER"
        upper = v.strip().upper()
        if upper not in {"USER", "ANALYST", "ADMIN", "AUDITOR"}:
            raise ValueError("Role must be one of: USER, ANALYST, ADMIN, AUDITOR.")
        return upper


class UserLoginRequest(BaseModel):
    """Authentication login request payload."""
    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., description="Account username")
    password: str = Field(..., description="Account plaintext password")


class TokenResponse(BaseModel):
    """Token response payload containing signed JWT and identity metadata."""
    access_token: str = Field(..., description="Signed compact JWT bearer token")
    token_type: str = Field(default="bearer", description="OAuth2 token type specification")
    expires_in_minutes: int = Field(..., description="Token lifespan duration in minutes")
    user_id: uuid.UUID = Field(..., description="Unique account identifier")
    username: str = Field(..., description="Authenticated username")
    role: str = Field(..., description="Assigned authorization role")


class UserResponse(BaseModel):
    """Public safe user representation (excludes password hash)."""
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
