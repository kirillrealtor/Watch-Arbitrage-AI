from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.catalog.infrastructure.models import (
    Brand,
    Source,
    Reference,
    WatchList,
    WatchListEntry,
    Alias,
)
from apps.api.infrastructure.repository import BaseRepository, TenantRepository


class BrandRepository(BaseRepository[Brand]):
    async def get_by_name(self, name: str) -> Brand | None:
        result = await self.session.execute(
            select(Brand).where(Brand.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Brand | None:
        result = await self.session.execute(
            select(Brand).where(Brand.slug == slug)
        )
        return result.scalar_one_or_none()


class SourceRepository(BaseRepository[Source]):
    pass


class ReferenceRepository(BaseRepository[Reference]):
    async def get_by_brand_and_ref_code(
        self, brand_id: str, ref_code: str
    ) -> Reference | None:
        result = await self.session.execute(
            select(Reference)
            .where(Reference.brand_id == brand_id)
            .where(Reference.ref_code == ref_code)
        )
        return result.scalar_one_or_none()


class WatchListRepository(TenantRepository[WatchList]):
    pass


class AliasRepository(BaseRepository[Alias]):
    async def find_by_alias_text(self, alias_text: str) -> list[Alias]:
        result = await self.session.execute(
            select(Alias).where(Alias.alias_text == alias_text)
        )
        return list(result.scalars().all())
