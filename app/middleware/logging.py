import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = structlog.get_logger()


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured logging with request/trace IDs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract trace/request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        trace_id = request.headers.get("X-Trace-ID") or request_id

        # Add to request state for use in handlers
        request.state.request_id = request_id
        request.state.trace_id = trace_id

        # Create logger with context
        log = logger.bind(
            request_id=request_id,
            trace_id=trace_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        # Log request start
        start_time = time.time()
        log.info("request_started")

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log response
            log.info(
                "request_completed",
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
            )

            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = trace_id

            return response

        except Exception as exc:
            process_time = time.time() - start_time
            log.error(
                "request_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                process_time_ms=round(process_time * 1000, 2),
                exc_info=True,
            )
            raise
