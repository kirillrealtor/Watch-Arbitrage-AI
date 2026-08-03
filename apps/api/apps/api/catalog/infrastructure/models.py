from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Text, UniqueConstraint, ForeignKey
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from apps.api.infrastructure.models import Base, TimestampMixin, ULIDMixin


class Brand(ULIDMixin, Base):
    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(Text(), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(Text(), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    references: Mapped[list["Reference"]] = relationship(back_populates="brand")


class Source(ULIDMixin, Base):
    __tablename__ = "sources"

    source_key: Mapped[str] = mapped_column(Text(), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(Text(), nullable=False)
    adapter_version: Mapped[str] = mapped_column(Text(), nullable=False)
    access_mode: Mapped[str] = mapped_column(Text(), nullable=False)
    rate_policy: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    approval_ref: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default=sa.text("false"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


class WatchList(ULIDMixin, Base):
    __tablename__ = "watch_lists"

    organization_id: Mapped[str] = mapped_column(
        Text(), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    entries: Mapped[list["WatchListEntry"]] = relationship(back_populates="watch_list")


class Reference(ULIDMixin, Base):
    __tablename__ = "references"

    brand_id: Mapped[str] = mapped_column(
        Text(), ForeignKey("brands.id"), nullable=False
    )
    ref_code: Mapped[str] = mapped_column(Text(), nullable=False)
    model_name: Mapped[str | None] = mapped_column(Text(), nullable=True)
    generation: Mapped[str | None] = mapped_column(Text(), nullable=True)
    attributes: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean(), default=True, server_default=sa.text("true"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("brand_id", "ref_code", name="uq_references_brand_ref"),)

    brand: Mapped[Brand] = relationship(back_populates="references")
    aliases: Mapped[list["Alias"]] = relationship(back_populates="reference")


class Alias(ULIDMixin, Base):
    __tablename__ = "aliases"

    reference_id: Mapped[str] = mapped_column(
        Text(), ForeignKey("references.id"), nullable=False
    )
    alias_text: Mapped[str] = mapped_column(Text(), nullable=False)
    source: Mapped[str | None] = mapped_column(Text(), nullable=True)

    __table_args__ = (UniqueConstraint("alias_text", "source", name="uq_aliases_text_source"),)

    reference: Mapped[Reference] = relationship(back_populates="aliases")


class WatchListEntry(ULIDMixin, Base):
    __tablename__ = "watch_list_entries"

    watch_list_id: Mapped[str] = mapped_column(
        Text(), ForeignKey("watch_lists.id"), nullable=False
    )
    reference_id: Mapped[str] = mapped_column(
        Text(), ForeignKey("references.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("watch_list_id", "reference_id", name="uq_watch_list_entries_list_ref"),
    )

    watch_list: Mapped[WatchList] = relationship(back_populates="entries")
