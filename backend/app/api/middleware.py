"""
API middleware and global exception handlers.

AccessLogMiddleware: emits one structured JSON log entry per request —
  method, path, status_code, processing_time_ms.
  Domain-specific fields (session_id, question_length, etc.) are logged
  separately by each route handler.

Global exception handler: catches any unhandled exception and returns a
  generic 500 so internal stack traces are never exposed to clients.
"""

import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger("rag_chatbot.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    Emits a structured access log entry for every HTTP request.

    Log fields:
      method, path, status_code, processing_time_ms

    Privacy: request/response bodies are NEVER read here.
    Also attaches X-Process-Time response header for debugging.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed_ms = int((time.time() - start) * 1000)

        response.headers["X-Process-Time"] = str(elapsed_ms)

        logger.info(
            "http_request",
            extra={
                "extra": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "processing_time_ms": elapsed_ms,
                }
            },
        )

        return response


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for any unhandled exception.
    Logs the traceback internally; returns a generic 500 to the caller
    so implementation details are never leaked.
    """
    logger.error(
        "unhandled_exception",
        exc_info=exc,
        extra={
            "extra": {
                "method": request.method,
                "path": request.url.path,
            }
        },
    )
    return JSONResponse(
        status_code=500,
        content={"error": "An internal server error occurred. Please try again."},
    )


def setup_middleware(app: FastAPI) -> None:
    """Register all middleware and exception handlers onto the app instance."""
    app.add_middleware(AccessLogMiddleware)
    app.add_exception_handler(Exception, global_exception_handler)
