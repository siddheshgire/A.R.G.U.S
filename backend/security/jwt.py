"""
A.R.G.U.S. — JWT Token Issuance & Verification
Stateless token handling with HS256 HMAC-SHA256 signature verification.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from fastapi import HTTPException, status

from backend.config import settings


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Encodes claims payload into a signed JSON Web Token (JWT).

    Parameters
    ----------
    data : Dict[str, Any]
        Claims to embed in token (sub, user_id, role, etc.).
    expires_delta : Optional[timedelta]
        Token lifetime duration. Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns
    -------
    str
        Compact signed JWT string.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),  # Unique token identifier
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and cryptographically validates a JWT token.

    Parameters
    ----------
    token : str
        The compact serialized JWT string.

    Returns
    -------
    Dict[str, Any]
        The verified claims payload.

    Raises
    ------
    HTTPException
        If the token is expired, tampered with, or malformed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "iat"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials; malformed or invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
