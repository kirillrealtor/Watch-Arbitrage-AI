from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from apps.api.schemas import HealthResponse


async def health_handler(request: Request) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", "unknown")
    return JSONResponse(
        content={"data": HealthResponse(status="ok", trace_id=trace_id).model_dump()}
    )
