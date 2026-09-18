"""
FastAPI application entry point.

Configures:
- SlowAPI rate limiting & custom 429 handler
- HTTP security headers middleware (nosniff, DENY frame, strict referrer, CSP)
- CORS middleware with strict credential origin isolation
- Lifespan events (MongoDB connect/disconnect + index creation)
- Router includes
- Global sanitized exception handling
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException as FastAPIHTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.database import connect_to_mongodb, close_mongodb_connection, create_indexes
from app.core.limiter import limiter
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.links import router as links_router
from app.api.redirect import router as redirect_router
from app.api.bio import router as bio_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    settings = get_settings()
    logger.info("Connecting to MongoDB at %s", settings.mongodb_uri)
    connect_to_mongodb()
    create_indexes()

    if settings.is_production:
        if "change-me" in settings.jwt_secret or len(settings.jwt_secret) < 32:
            logger.critical("SECURITY WARNING: Running in production with insecure or default JWT_SECRET!")

    yield

    # Shutdown
    logger.info("Closing MongoDB connection.")
    close_mongodb_connection()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="SphereSphere",
        description="SphereSphere is a secure full-stack platform for creating short links, tracking privacy-conscious click analytics, generating customizable QR codes, and building public Bio-Link pages.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Attach SlowAPI limiter state & middleware
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    # CORS configuration
    cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if settings.frontend_url not in cors_origins:
        cors_origins.append(settings.frontend_url)
    if "*" in cors_origins:
        logger.warning("CORS wildcard '*' with credentials is not permitted; filtering out '*'.")
        cors_origins = [o for o in cors_origins if o != "*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # HTTP Security Headers Middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' http://localhost:* ws://localhost:* https:; "
            "frame-ancestors 'none';"
        )
        return response

    # Rate limit exceeded exception handler
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": f"Rate limit exceeded: {exc.detail}"},
            headers={"Retry-After": "60"},
        )

    # Global unhandled exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        if isinstance(exc, RateLimitExceeded):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": f"Rate limit exceeded: {exc.detail}"},
                headers={"Retry-After": "60"},
            )
        if isinstance(exc, (FastAPIHTTPException, StarletteHTTPException)):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=getattr(exc, "headers", None),
            )
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred."},
        )

    # Include routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(links_router)
    app.include_router(redirect_router)
    app.include_router(bio_router)

    return app


app = create_app()
