from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    trace_id: str


class ReadyResponse(BaseModel):
    status: str
    database: str
    trace_id: str


class ApiError(BaseModel):
    code: str
    message: str
    field_errors: dict[str, list[str]] | None = None
    trace_id: str
    retryable: bool = False


class ApiSuccessEnvelope(BaseModel):
    data: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None
