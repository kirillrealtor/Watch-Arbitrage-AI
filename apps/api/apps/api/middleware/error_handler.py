from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

try:
    from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT  # noqa: F811

    _HTTP_422 = HTTP_422_UNPROCESSABLE_CONTENT
except ImportError:
    _HTTP_422 = HTTP_422_UNPROCESSABLE_ENTITY

from apps.api.schemas import ApiError

logger = logging.getLogger("chronoarb.api")


async def pydantic_validation_handler(
    _request: Request, exc: PydanticValidationError
) -> JSONResponse:
    trace_id = getattr(_request.state, "trace_id", "unknown")
    field_errors: dict[str, list[str]] = {}
    for error in exc.errors():
        loc = ".".join(str(p) for p in error["loc"])
        msg = error["msg"]
        field_errors.setdefault(loc, []).append(msg)

    api_error = ApiError(
        code="VALIDATION_ERROR",
        message="One or more fields are invalid.",
        field_errors=field_errors,
        trace_id=trace_id,
        retryable=False,
    )
    logger.warning("validation_error", extra={"trace_id": trace_id, "errors": field_errors})
    return JSONResponse(
        status_code=_HTTP_422,
        content={"error": api_error.model_dump()},
    )


async def generic_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    trace_id = getattr(_request.state, "trace_id", "unknown")
    logger.exception("unhandled_error", extra={"trace_id": trace_id})
    api_error = ApiError(
        code="INTERNAL_ERROR",
        message="An internal error occurred.",
        trace_id=trace_id,
        retryable=True,
    )
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": api_error.model_dump()},
    )
