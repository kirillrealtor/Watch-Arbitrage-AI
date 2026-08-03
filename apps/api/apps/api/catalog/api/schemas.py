from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    created_at: datetime


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_key: str
    display_name: str
    adapter_version: str
    access_mode: str
    is_enabled: bool
    created_at: datetime


class ReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    brand_id: str
    ref_code: str
    model_name: str | None = None
    generation: str | None = None
    is_active: bool
    created_at: datetime


class WatchListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    created_at: datetime


class WatchListEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    watch_list_id: str
    reference_id: str
    created_at: datetime
