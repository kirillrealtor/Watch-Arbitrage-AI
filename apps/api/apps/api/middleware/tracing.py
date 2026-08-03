from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("chronoarb.api")


class TraceIdMiddleware(BaseHTTPMiddleware):
    HEADER_NAME: str = "X-Trace-Id"

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        trace_id = request.headers.get(self.HEADER_NAME, f"trc_{uuid.uuid4().hex[:26]}")
        request.state.trace_id = trace_id

        response = await call_next(request)
        response.headers[self.HEADER_NAME] = trace_id

        logger.info(
            "request",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
            },
        )

        return response
