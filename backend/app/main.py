"""
RAG-TRACK FastAPI Application.

Main application entry point with middleware, routing, and observability.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.ratelimit import limiter, rate_limit_exceeded_handler
from app.core.auth import get_api_key
from slowapi.errors import RateLimitExceeded
from app.api import ingest, retrieve

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    logger.info(f"Starting {settings.app_name} in {settings.environment} mode")
    logger.info(f"Data directory: {settings.data_dir}")
    logger.info(
        f"Rate limiting: {'enabled' if settings.rate_limit_enabled else 'disabled'}"
    )
    logger.info(
        f"API Authentication: {'enabled' if settings.api_key else 'disabled (dev mode)'}"
    )

    # Ensure data directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_store_dir.mkdir(parents=True, exist_ok=True)

    yield

    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="An End-to-End, Observable Retrieval-Augmented Generation (RAG) System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Configure CORS from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.debug(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.debug(f"{request.method} {request.url.path} - {response.status_code}")
    return response


# Include routers
app.include_router(ingest.router, prefix="/ingest", tags=["Ingestion"])
app.include_router(retrieve.router, prefix="/query", tags=["Query"])


@app.get("/")
def root():
    """Root endpoint with application info."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check(request: Request):
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
    }


@app.get("/health/ready")
def readiness_check(request: Request):
    """Readiness check with dependency validation."""
    checks = {
        "api": "ready",
        "auth": "enabled" if settings.api_key else "disabled",
    }

    # Check if required directories are writable
    try:
        settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        checks["storage"] = f"error: {str(e)}"

    all_ready = all(v == "ready" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ready else 503,
        content={
            "status": "ready" if all_ready else "not_ready",
            "checks": checks,
        },
    )
