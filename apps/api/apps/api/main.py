from __future__ import annotations

import logging

from fastapi import FastAPI
from pydantic import ValidationError as PydanticValidationError

from apps.api.middleware.error_handler import (
    generic_exception_handler,
    pydantic_validation_handler,
)
from apps.api.middleware.tracing import TraceIdMiddleware
from apps.api.routes.health import health_handler
from apps.api.routes.ready import ready_handler
from apps.api.settings import settings

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s trace_id=%(trace_id)s %(message)s",
)
logger = logging.getLogger("chronoarb.api")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    app.add_middleware(TraceIdMiddleware)

    app.add_exception_handler(PydanticValidationError, pydantic_validation_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.add_api_route(
        "/health",
        health_handler,
        methods=["GET"],
        include_in_schema=False,
    )
    app.add_api_route(
        "/ready",
        ready_handler,
        methods=["GET"],
        include_in_schema=False,
    )

    logger.info("app_started", extra={"trace_id": "bootstrap"})

    return app


app = create_app()
