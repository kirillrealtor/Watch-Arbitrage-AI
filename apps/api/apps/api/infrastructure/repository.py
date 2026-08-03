from __future__ import annotations

from typing import TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from apps.api.infrastructure.database import async_session

Model = TypeVar("Model", bound=DeclarativeBase)


class BaseRepository[Model]:
    def __init__(self, session: AsyncSession | None = None) -> None:
        if session is None:
            raise TypeError(
                f"{type(self).__name__} requires a session. "
                "Provide session= directly or use UnitOfWork.repository()."
            )
        self.session = session

    async def get_by_id(self, model_cls: type[Model], id: str) -> Model | None:
        return await self.session.get(model_cls, id)

    async def list_all(
        self,
        model_cls: type[Model],
        limit: int = 50,
        offset: int = 0,
    ) -> list[Model]:
        result = await self.session.execute(
            select(model_cls).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self, model_cls: type[Model]) -> int:
        result = await self.session.execute(select(func.count()).select_from(model_cls))
        return result.scalar_one()

    async def save(self, model: Model) -> Model:
        self.session.add(model)
        await self.session.flush()
        return model

    async def delete(self, model: Model) -> None:
        await self.session.delete(model)
        await self.session.flush()


class TenantRepository[Model](BaseRepository[Model]):
    def __init__(self, session: AsyncSession | None = None, model_cls: type[Model] | None = None) -> None:
        super().__init__(session)
        if model_cls is not None and "organization_id" not in model_cls.__table__.columns:
            raise TypeError(
                f"TenantRepository requires a model with an 'organization_id' column. "
                f"{model_cls.__name__} does not have one. "
                "Use BaseRepository for non-tenant models."
            )

    async def get_by_id(
        self, model_cls: type[Model], id: str, organization_id: str
    ) -> Model | None:
        model = await self.session.get(model_cls, id)
        if model is None:
            return None
        org_id = getattr(model, "organization_id", None)
        if org_id is None or org_id != organization_id:
            return None
        return model

    async def list_by_org(
        self,
        model_cls: type[Model],
        organization_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Model]:
        result = await self.session.execute(
            select(model_cls)
            .where(getattr(model_cls, "organization_id") == organization_id)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
