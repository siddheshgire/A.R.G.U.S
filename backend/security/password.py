"""
A.R.G.U.S. — Password Hashing & Verification
Cryptographic utility module using bcrypt for salt generation and constant-time verification.
"""

import bcrypt


def hash_password(plain_password: str) -> str:
    """
    Hashes a plaintext password using bcrypt with a securely generated per-password salt.
    
    Parameters
    ----------
    plain_password : str
        The raw plaintext password supplied by the user.

    Returns
    -------
    str
        The resulting bcrypt hash string (including salt, cost factor, and hash).
    """
    if not plain_password:
        raise ValueError("Password cannot be empty.")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a stored bcrypt hash in constant time.

    Parameters
    ----------
    plain_password : str
        Plaintext candidate password.
    hashed_password : str
        Stored bcrypt hash.

    Returns
    -------
    bool
        True if the password matches the hash, False otherwise.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def validate_password_strength(password: str) -> None:
    """
    Validates that a password satisfies minimum security complexity requirements.
    Raises ValueError if criteria are not met.
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters in length.")
    if len(password) > 128:
        raise ValueError("Password length cannot exceed 128 characters.")
