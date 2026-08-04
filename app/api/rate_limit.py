"""Rate limiting configuration using slowapi.

Enforcement is applied per-route via the @limiter.limit(RATE_LIMIT) decorator
rather than SlowAPIMiddleware. SlowAPIMiddleware is built on Starlette's
BaseHTTPMiddleware, which has a known issue where exceptions raised deep in a
route handler can bypass FastAPI's registered exception handlers and escape as a
raw ASGI crash - skipping CORSMiddleware in the process, so the browser reports
a misleading "CORS blocked" error instead of the real one. The decorator-based
approach checks the limit before calling the route and raises RateLimitExceeded,
which flows through the normal exception-handling stack (and thus CORSMiddleware)
like any other handled exception.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

RATE_LIMIT = f"{settings.rate_limit_per_minute}/minute"

limiter = Limiter(key_func=get_remote_address)
