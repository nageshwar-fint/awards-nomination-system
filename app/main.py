import structlog
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse

from app.api.v1.auth import limiter, router as auth_router
from app.api.v1.routes import router as v1_router
from app.config import get_settings
from slowapi.errors import RateLimitExceeded
from app.core.errors import (
    AppError,
    app_error_handler,
    generic_exception_handler,
    permission_error_handler,
    validation_error_handler,
    value_error_handler,
)
from app.middleware.logging import StructuredLoggingMiddleware

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Awards Nomination System API",
    description="Employee recognition system for nominations and awards",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429,
    content={"error": {"message": "Rate limit exceeded. Please try again later.", "type": "RateLimitError"}}
))

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add structured logging middleware
app.add_middleware(StructuredLoggingMiddleware)

# Register error handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(PermissionError, permission_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(v1_router, prefix="/api/v1", tags=["v1"])


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger = structlog.get_logger()
    logger.info("application_started", environment=settings.app_env)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger = structlog.get_logger()
    logger.info("application_shutting_down")
