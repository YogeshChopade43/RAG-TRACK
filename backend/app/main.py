"""
RAG-TRACK FastAPI Application.

Main application entry point with middleware, routing, and observability.
"""

import asyncio
import logging
import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import faiss
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.api import auth, ingest, retrieve
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.observability import setup_opentelemetry
from app.core.ratelimit import limiter, rate_limit_exceeded_handler
from app.db.session import init_db

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)

frontend_dist = Path("/app/frontend/dist")  # built into the container image


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    setup_opentelemetry()

    # Database is optional: only auth endpoints need it (they return 503 without it)
    if settings.database_url:
        try:
            init_db()
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Database initialization failed, auth endpoints will be unavailable: {e}")
    else:
        logger.info("DATABASE_URL not set — skipping database initialization")

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

    cleanup_task = (
        asyncio.create_task(_trace_cleanup_loop()) if settings.trace_retention_days > 0 else None
    )

    yield

    if cleanup_task:
        cleanup_task.cancel()
    logger.info("Shutdown complete")


async def _trace_cleanup_loop() -> None:
    """Delete traces older than TRACE_RETENTION_DAYS now and then once a day (they contain document text)."""
    from app.services.observability.trace_storage import TraceStorage

    while True:
        try:
            await asyncio.to_thread(TraceStorage.cleanup_old_traces, settings.trace_retention_days)
        except Exception as e:
            logger.warning(f"Trace cleanup failed: {e}")
        await asyncio.sleep(24 * 3600)


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


# Browser security headers. The CSP matters most: users keep their OpenRouter key in
# sessionStorage, so any injected script could read it. Only the app's own scripts
# run, and the page can only talk to this origin.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",  # toast/radix inject <style>; style injection can't read storage
        "img-src 'self' data:",
        "font-src 'self' data:",  # Vite inlines small font subsets as data: URLs
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    # Swagger UI / ReDoc load scripts from a CDN and run inline code
    if not request.url.path.startswith(("/docs", "/redoc")):
        response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.debug(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.debug(f"{request.method} {request.url.path} - {response.status_code}")
    return response


# Request correlation middleware
@app.middleware("http")
async def request_correlation(request: Request, call_next):
    """Add X-Request-ID to all requests for tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingestion"])
app.include_router(retrieve.router, prefix="/query", tags=["Query"])


@app.get("/")
async def root(request: Request):
    """Root endpoint - serves frontend or returns app info."""
    if frontend_dist.exists():
        return await StaticFiles(directory=str(frontend_dist), html=True).get_response("index.html", request.scope)
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
        "environment": settings.environment,
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
        test_file = settings.vector_store_dir / ".write_test"
        test_file.write_text("ok")
        test_file.unlink()
        checks["storage"] = "ready"
    except Exception as e:
        checks["storage"] = f"error: {str(e)}"

    # Check FAISS index creation capability
    try:
        faiss.IndexFlatL2(2)
        checks["vector_engine"] = "ready"
    except Exception as e:
        checks["vector_engine"] = f"error: {str(e)}"

    # Check trace storage
    try:
        from app.services.observability.trace_storage import TraceStorage
        traces_dir = TraceStorage._get_traces_dir()
        os.makedirs(traces_dir, exist_ok=True)
        checks["trace_storage"] = "ready"
    except Exception as e:
        checks["trace_storage"] = f"error: {str(e)}"

    degraded = [k for k, v in checks.items() if v != "ready"]
    status = "ready" if not degraded else "degraded"
    status_code = 200 if not degraded else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "checks": checks,
            "degraded_components": degraded,
        },
    )


@app.get("/health/startup")
def startup_check(request: Request):
    """Startup probe for container orchestration."""
    return {
        "status": "started",
        "service": settings.app_name,
        "environment": settings.environment,
    }


if frontend_dist.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(frontend_dist), html=True),
        name="frontend-static",
    )

    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        """Serve frontend for client-side routes."""
        file_path = frontend_dist / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return await StaticFiles(directory=str(frontend_dist)).get_response(full_path, request.scope)
        return await StaticFiles(directory=str(frontend_dist), html=True).get_response("index.html", request.scope)
