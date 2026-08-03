from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

from apps.api.deps import get_db_status
from apps.api.schemas import ReadyResponse


async def ready_handler(request: Request) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", "unknown")
    db_status = await get_db_status()
    is_connected = db_status == "connected"
    return JSONResponse(
        content={
            "data": ReadyResponse(
                status="ok" if is_connected else "error",
                database=db_status,
                trace_id=trace_id,
            ).model_dump()
        },
        status_code=status.HTTP_200_OK if is_connected else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
