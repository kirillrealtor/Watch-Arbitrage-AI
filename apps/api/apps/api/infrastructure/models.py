from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import TIMESTAMP, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )


class ULIDMixin:
    id: Mapped[str] = mapped_column(Text(), primary_key=True)


class TenantMixin:
    organization_id: Mapped[str] = mapped_column(Text(), nullable=False)
