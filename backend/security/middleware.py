"""
A.R.G.U.S. — Security Headers & In-Memory Rate Limiting Middleware
Applies defensive HTTP response headers and protects against denial-of-service/brute-force.
"""

import time
from typing import Dict, List
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from backend.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware injecting standard defensive HTTP headers to mitigate XSS, clickjacking,
    and MIME-type sniffing vulnerabilities, without breaking OpenAPI/Swagger UI.
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Content Security Policy configured to allow Swagger CDN assets during development
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com;"
        )
        return response


class InMemoryRateLimiter:
    """
    Lightweight sliding-window rate limiter per client IP address.
    Does not require external message queues or caching servers (Redis/Kafka).
    """

    def __init__(self, requests_per_window: int = 100, window_seconds: int = 60):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.client_requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds
        
        # Filter out timestamps older than the active window
        timestamps = [t for t in self.client_requests[client_ip] if t > window_start]
        
        if len(timestamps) >= self.requests_per_window:
            self.client_requests[client_ip] = timestamps
            return False

        timestamps.append(now)
        self.client_requests[client_ip] = timestamps
        return True


# Singleton rate limiter instance
rate_limiter = InMemoryRateLimiter(
    requests_per_window=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware enforcing sliding-window rate limits per client IP.
    """

    async def dispatch(self, request: Request, call_next):
        # Exempt health and docs endpoints from strict rate limiting
        exempt_paths = {"/health", "/docs", "/openapi.json", "/redoc"}
        if request.url.path in exempt_paths:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please slow down and try again later.",
                    }
                },
                headers={"Retry-After": str(rate_limiter.window_seconds)},
            )

        return await call_next(request)
