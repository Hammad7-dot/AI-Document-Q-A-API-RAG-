"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.error_handlers import register_error_handlers
from app.api.rate_limit import limiter
from app.api.routes.auth import router as auth_router
from app.api.routes.auth import users_router
from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.startup_checks import validate_embedding_dimension

configure_logging(settings.debug)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_embedding_dimension(settings)
    logger.info("app_startup", environment=settings.environment)
    yield
    logger.info("app_shutdown")


app = FastAPI(
    title=settings.app_name,
    description="Production-ready Retrieval Augmented Generation (RAG) backend API.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda r, e: r.app.state.limiter._rate_limit_exceeded_handler(r, e))

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(health_router)


@app.get("/")
async def root() -> dict:
    """Basic root endpoint."""
    return {"name": settings.app_name, "status": "running", "docs": "/docs"}
