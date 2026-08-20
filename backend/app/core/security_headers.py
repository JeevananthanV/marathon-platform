import time
import collections
from typing import Dict, Deque, Tuple, Optional
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from app.core.config import settings
from app.core.logging import logger


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Appends OWASP recommended HTTP security headers to all responses.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Standard OWASP & Production Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=*"
        
        # HSTS (1 year + subdomains)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Content-Security-Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https: blob:; "
            "script-src 'self' 'unsafe-inline' https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )

        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding window in-memory rate limiter per client IP address.
    Protects public registration, payment, webhook, and administrative endpoints against abuse.
    """

    def __init__(self, app, default_limit: int = 150, window_seconds: int = 60):
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        # In-memory storage: IP -> deque of timestamps
        self._clients: Dict[str, Deque[float]] = collections.defaultdict(collections.deque)

        # Path-specific rate limit overrides (e.g. stricter limits for payment and admin auth)
        self._path_limits = {
            "/api/v1/registrations/initiate": 30,
            "/api/v1/payments/verify": 30,
            "/api/v1/admin": 60,
        }

    def _get_client_ip(self, request: Request) -> str:
        # Check standard proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def _get_limit_for_path(self, path: str, client_ip: str) -> int:
        if client_ip in ["127.0.0.1", "testclient"]:
            return 10000
        for prefix, limit in self._path_limits.items():
            if path.startswith(prefix):
                return limit
        return self.default_limit

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Bypass rate limiting for health check, docs, static assets
        if path in ["/health", "/api/health", "/favicon.ico"] or path.startswith("/api/v1/docs") or path.startswith("/api/v1/openapi.json"):
            return await call_next(request)

        # Allow test suite to disable rate limiting if needed
        if getattr(settings, "DISABLE_RATE_LIMIT", False):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()
        window_start = now - self.window_seconds
        limit = self._get_limit_for_path(path, client_ip)

        timestamps = self._clients[client_ip]

        # Evict timestamps outside sliding window
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        current_count = len(timestamps)

        if current_count >= limit:
            retry_after = int(self.window_seconds - (now - timestamps[0])) if timestamps else self.window_seconds
            logger.warning(f"[RATE LIMIT] IP {client_ip} exceeded limit on {path} ({current_count}/{limit})")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Try again in {max(1, retry_after)} seconds.",
                    "retry_after_seconds": max(1, retry_after),
                },
                headers={
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + retry_after)),
                },
            )

        # Record this request
        timestamps.append(now)

        response = await call_next(request)

        # Append rate limit headers
        remaining = max(0, limit - len(timestamps))
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.window_seconds))

        return response
