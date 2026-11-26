"""FastAPI entry point for VibeVerse AI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.api.routes import (
    analytics,
    cross_domain,
    discovery,
    health,
    interactions,
    personality,
    preferences,
)
from backend.core.config import get_settings
from backend.core.logging_config import setup_logging

settings = get_settings()
logger = setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize startup resources cleanly."""
    logger.info("Starting %s backend (%s)", settings.app_name, settings.app_env)
    yield
    logger.info("Shutting down %s backend", settings.app_name)


app = FastAPI(
    title="VibeVerse AI API",
    description="Cross-Domain Music, Movies & Web Series Intelligence and Recommendation API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database errors safely without leaking credentials."""
    logger.error("Database error on %s: %s", request.url.path, exc.__class__.__name__)
    return JSONResponse(
        status_code=503,
        content={
            "error": "DatabaseUnavailable",
            "detail": "The database service is currently unavailable or not initialized. Please check your MySQL configuration.",
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return clean validation error messages."""
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "detail": "One or more request parameters are invalid.",
            "extra": {"errors": exc.errors()},
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all safe error handler."""
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "detail": "An unexpected error occurred while processing your request.",
        },
    )


app.include_router(health.router)
app.include_router(preferences.router)
app.include_router(discovery.router)
app.include_router(cross_domain.router)
app.include_router(personality.router)
app.include_router(interactions.router)
app.include_router(analytics.router)


@app.get("/", tags=["Root"])
def root():
    """Root welcome endpoint."""
    return {
        "app": settings.app_name,
        "tagline": "Your vibe. Your soundtrack. Your next obsession.",
        "docs": "/docs",
        "health": "/health",
    }
