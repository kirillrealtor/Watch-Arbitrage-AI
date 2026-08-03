from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.api.infrastructure.database import async_session as default_sessionmaker
from apps.api.infrastructure.repository import BaseRepository, TenantRepository


class UnitOfWork:
    def __init__(
        self,
        session: AsyncSession | None = None,
        sessionmaker: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.session = session
        self._sessionmaker = sessionmaker or default_sessionmaker
        self._owns_session = session is None

    async def __aenter__(self) -> UnitOfWork:
        if self.session is None:
            self.session = self._sessionmaker()
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._owns_session and self.session is not None:
            await self.session.close()

    async def commit(self) -> None:
        if self.session is None:
            raise RuntimeError(
                "Cannot commit: no active session. "
                "Use 'async with UnitOfWork() as uow:' to create a session context."
            )
        await self.session.commit()

    async def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError(
                "Cannot rollback: no active session. "
                "Use 'async with UnitOfWork() as uow:' to create a session context."
            )
        await self.session.rollback()

    def repository(self, repo_cls: type[BaseRepository]) -> BaseRepository:
        return repo_cls(self.session)

    def tenant_repository(self, repo_cls: type[TenantRepository]) -> TenantRepository:
        return repo_cls(self.session)
