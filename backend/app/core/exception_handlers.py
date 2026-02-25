import logging
import traceback
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import DentalOSError

logger = logging.getLogger("dentalos.errors")


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI application."""

    @app.exception_handler(DentalOSError)
    async def dentalos_error_handler(request: Request, exc: DentalOSError) -> JSONResponse:
        log_context = _build_log_context(request, exc)

        if exc.status_code >= 500:
            logger.error(
                "Server error: %s (code=%s, status=%d, trace_id=%s)",
                exc.message,
                exc.error,
                exc.status_code,
                log_context["trace_id"],
                extra=log_context,
            )
        elif exc.status_code >= 400:
            logger.warning(
                "Client error: %s (code=%s, status=%d)",
                exc.error,
                exc.message,
                exc.status_code,
                extra=log_context,
            )

        return _build_error_response(exc.status_code, exc.error, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        field_errors: dict[str, list[str]] = {}
        for error in exc.errors():
            loc = error.get("loc", ())
            field_path = ".".join(str(part) for part in loc if part != "body")
            if not field_path:
                field_path = "__root__"
            field_errors.setdefault(field_path, []).append(error.get("msg", "Invalid value"))

        return _build_error_response(
            status_code=422,
            error="VALIDATION_failed",
            message="Validation errors occurred.",
            details=field_errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        error_map = {
            400: "SYSTEM_bad_request",
            404: "SYSTEM_not_found",
            405: "SYSTEM_method_not_allowed",
            429: "SYSTEM_rate_limit_exceeded",
            500: "SYSTEM_internal_error",
        }
        error_code = error_map.get(exc.status_code, f"SYSTEM_http_{exc.status_code}")

        return _build_error_response(
            status_code=exc.status_code,
            error=error_code,
            message=str(exc.detail) if exc.detail else "An error occurred.",
            details={},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        trace_id = str(uuid4())

        logger.critical(
            "Unhandled exception (trace_id=%s): %s",
            trace_id,
            str(exc),
            extra={
                "trace_id": trace_id,
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
                "traceback": traceback.format_exc(),
            },
            exc_info=True,
        )

        return _build_error_response(
            status_code=500,
            error="SYSTEM_internal_error",
            message="An unexpected error occurred. Please try again later.",
            details={"trace_id": trace_id},
        )


def _build_error_response(
    status_code: int,
    error: str,
    message: str,
    details: dict,  # type: ignore[type-arg]
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "message": message,
            "details": details,
        },
    )


def _build_log_context(request: Request, exc: DentalOSError) -> dict[str, object]:
    return {
        "trace_id": str(uuid4()),
        "error_code": exc.error,
        "status_code": exc.status_code,
        "path": request.url.path,
        "method": request.method,
        "tenant_id": getattr(request.state, "tenant_id", None),
        "user_id": getattr(request.state, "user_id", None),
    }
