from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: str
    role: str
    invited_by: str | None = None
    created_at: datetime
