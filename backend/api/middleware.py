"""
Middleware and error handlers for FastAPI application
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time
from typing import Callable


async def error_handler_middleware(request: Request, call_next: Callable):
    """
    Global error handler middleware

    Catches unhandled exceptions and returns proper JSON responses.
    Also adds request timing.
    """
    start_time = time.time()

    try:
        response = await call_next(request)

        # Add processing time header
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(round(process_time, 3))

        return response

    except Exception as exc:
        # Log the error (in production, use proper logging)
        print(f"Unhandled error: {str(exc)}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error occurred",
                "error_type": type(exc).__name__
            }
        )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler for Pydantic validation errors

    Returns detailed validation error messages in a user-friendly format.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )
