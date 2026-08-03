from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from apps.api.deps import get_db_status
from apps.api.schemas import ReadyResponse


async def ready_handler(request: Request) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", "unknown")
    db_status = await get_db_status()
    return JSONResponse(
        content={
            "data": ReadyResponse(
                status="ok" if db_status == "connected" else "degraded",
                database=db_status,
                trace_id=trace_id,
            ).model_dump()
        }
    )
