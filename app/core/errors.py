from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle application errors with consistent format and CORS headers."""
    from app.config import get_settings
    settings = get_settings()
    
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "type": type(exc).__name__,
                "details": exc.details,
            },
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    
    # Explicitly add CORS headers to ensure they're present
    origin = request.headers.get("origin")
    if origin and (settings.cors_origins == "*" or origin in settings.cors_origins_list):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Validation error",
                "type": "ValidationError",
                "details": exc.errors(),
            },
            "request_id": getattr(request.state, "request_id", None),
        },
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError exceptions."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "message": str(exc),
                "type": "ValueError",
                "details": {},
            },
            "request_id": getattr(request.state, "request_id", None),
        },
    )


async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
    """Handle PermissionError exceptions."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": {
                "message": str(exc),
                "type": "PermissionError",
                "details": {},
            },
            "request_id": getattr(request.state, "request_id", None),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions with CORS headers."""
    from app.config import get_settings
    import traceback
    
    settings = get_settings()
    
    # Log the full error for debugging
    import structlog
    logger = structlog.get_logger()
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        traceback=traceback.format_exc()
    )
    
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "Internal server error",
                "type": type(exc).__name__,
                "details": {"error": str(exc)} if not settings.is_production else {},
            },
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    
    # Explicitly add CORS headers to ensure they're present
    origin = request.headers.get("origin")
    if origin and (settings.cors_origins == "*" or origin in settings.cors_origins_list):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response
