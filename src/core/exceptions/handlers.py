"""Exception handlers — maps exception types to ErrorEnvelope JSON responses."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Internal
from src.core.exceptions.base import CoreException
from src.core.exceptions.envelope import ErrorEnvelope
from src.utils.logging import setup_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

logger = setup_logger(__name__)


async def _core_exception_handler(request: Request, exc: CoreException) -> JSONResponse:
    envelope = ErrorEnvelope.from_exception(code=exc.code, message=exc.message, detail=exc.detail)
    return JSONResponse(status_code=exc.status_code, content=envelope.model_dump())


async def _validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    envelope = ErrorEnvelope.from_exception(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        detail=str(exc.errors()),
    )
    return JSONResponse(status_code=422, content=envelope.model_dump())


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    envelope = ErrorEnvelope.from_exception(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
    )
    return JSONResponse(status_code=500, content=envelope.model_dump())


def add_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app.

    Args:
        app (FastAPI): The application instance.

    """
    app.add_exception_handler(CoreException, _core_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)