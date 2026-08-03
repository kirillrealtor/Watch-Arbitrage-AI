from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.identity.infrastructure.models import Organization, User, Membership
from apps.api.infrastructure.repository import BaseRepository, TenantRepository


class OrganizationRepository(BaseRepository[Organization]):
    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()


class UserRepository(BaseRepository[User]):
    async def get_by_cognito_sub(self, cognito_sub: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.cognito_sub == cognito_sub)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()


class MembershipRepository(TenantRepository[Membership]):
    async def get_by_user_and_org(
        self, user_id: str, organization_id: str
    ) -> Membership | None:
        result = await self.session.execute(
            select(Membership)
            .where(Membership.user_id == user_id)
            .where(Membership.organization_id == organization_id)
        )
        return result.scalar_one_or_none()

    async def list_members(self, organization_id: str) -> list[Membership]:
        result = await self.session.execute(
            select(Membership)
            .where(Membership.organization_id == organization_id)
        )
        return list(result.scalars().all())
