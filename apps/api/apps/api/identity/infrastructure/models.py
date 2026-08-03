from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Text, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from apps.api.infrastructure.models import Base, TimestampMixin, ULIDMixin


class Organization(ULIDMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(Text(), nullable=False)
    slug: Mapped[str] = mapped_column(Text(), unique=True, nullable=False)
    settings: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )

    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")

    def __repr__(self) -> str:
        return f"<Organization {self.slug}>"


class User(ULIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    cognito_sub: Mapped[str] = mapped_column(Text(), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(Text(), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text(), nullable=True)

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="user", foreign_keys="Membership.user_id"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Membership(ULIDMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_org"),)

    organization_id: Mapped[str] = mapped_column(
        Text(), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        Text(), ForeignKey("users.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text(), nullable=False)
    invited_by: Mapped[str | None] = mapped_column(
        Text(), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    organization: Mapped[Organization] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(
        back_populates="memberships", foreign_keys=[user_id]
    )

    def __repr__(self) -> str:
        return f"<Membership {self.role}>"
