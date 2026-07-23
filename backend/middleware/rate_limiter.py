import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("capsule.rate_limiter")

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Zero-dependency sliding-window rate limiter middleware.
    Prevents API/webhook brute-forcing and free-tier compute resource exhaustion.
    """
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_requests = defaultdict(list)

    def _clean_old_requests(self, client_ip: str, now: float):
        cutoff = now - 60.0
        self.client_requests[client_ip] = [
            ts for ts in self.client_requests[client_ip] if ts > cutoff
        ]

    async def dispatch(self, request: Request, call_next):
        # Exclude healthcheck and static docs
        path = request.url.path
        if path == "/" or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        self._clean_old_requests(client_ip, now)

        if len(self.client_requests[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP {client_ip} on path {path}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and try again later."
            )

        self.client_requests[client_ip].append(now)
        response = await call_next(request)
        return response
