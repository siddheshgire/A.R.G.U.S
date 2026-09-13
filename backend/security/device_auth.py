"""
A.R.G.U.S. — IoT Device Authentication & Verification Utilities
Provides SHA-256 API key hashing, constant-time verification, and header extraction.
"""

import hashlib
import secrets
from typing import Optional, Tuple
from fastapi import Request

from database.models.device import Device


def hash_device_key(raw_key: str) -> str:
    """Computes SHA-256 cryptographic digest of raw terminal API key."""
    if not raw_key:
        return ""
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()


def verify_device_credentials(device: Device, raw_key: str) -> bool:
    """
    Verifies presented raw key against the stored SHA-256 hash using constant-time comparison.
    Resists timing side-channel analysis.
    """
    if not device.api_key_hash or not raw_key:
        return False
    computed_hash = hash_device_key(raw_key)
    return secrets.compare_digest(computed_hash, device.api_key_hash)


async def extract_device_credentials(request: Request) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts device identification and credential from HTTP headers (primary)
    or request JSON payload (fallback).
    Headers:
      - X-Device-Code (or X-Device-ID)
      - X-Device-API-Key (or X-API-Key)
    """
    # 1. Header-based extraction (preferred IoT transport contract)
    device_code = request.headers.get("X-Device-Code") or request.headers.get("X-Device-ID")
    api_key = request.headers.get("X-Device-API-Key") or request.headers.get("X-API-Key")

    if device_code and api_key:
        return device_code.strip(), api_key.strip()

    # 2. JSON Payload fallback
    try:
        body = await request.json()
        if isinstance(body, dict):
            body_code = body.get("device_code") or body.get("device_id")
            body_key = body.get("api_key") or body.get("device_api_key")
            if body_code and body_key:
                return str(body_code).strip(), str(body_key).strip()
            # If code is in body and key in header, or vice versa
            if not device_code and body_code:
                device_code = str(body_code).strip()
            if not api_key and body_key:
                api_key = str(body_key).strip()
    except Exception:
        pass

    return device_code, api_key
