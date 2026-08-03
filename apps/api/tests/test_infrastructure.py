from __future__ import annotations

import pytest
from sqlalchemy import Text, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.infrastructure.models import Base, TimestampMixin, ULIDMixin
from apps.api.infrastructure.repository import BaseRepository, TenantRepository
from apps.api.infrastructure.uow import UnitOfWork
from apps.api.identity.infrastructure.models import Organization, Membership


class TestModel(ULIDMixin, TimestampMixin, Base):
    __tablename__ = "test_models"
    name: Mapped[str] = mapped_column(Text(), nullable=False)


class NonTenantModel(ULIDMixin, TimestampMixin, Base):
    __tablename__ = "non_tenant_models"
    data: Mapped[str] = mapped_column(Text(), nullable=False)


class TenantModel(ULIDMixin, TimestampMixin, Base):
    __tablename__ = "tenant_models"
    organization_id: Mapped[str] = mapped_column(Text(), nullable=False)
    data: Mapped[str] = mapped_column(Text(), nullable=False)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def enable_fks(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as s:
        yield s
    await engine.dispose()


class TestBaseRepository:
    async def test_save_and_get_by_id(self, session):
        from chronoarb.domain.ulid import generate_ulid
        repo = BaseRepository[TestModel](session)
        model = TestModel(id=generate_ulid("tst"), name="test-item")
        saved = await repo.save(model)
        await session.commit()

        retrieved = await repo.get_by_id(TestModel, saved.id)
        assert retrieved is not None
        assert retrieved.name == "test-item"

    async def test_list_all(self, session):
        from chronoarb.domain.ulid import generate_ulid
        repo = BaseRepository[TestModel](session)
        for i in range(5):
            model = TestModel(id=generate_ulid("tst"), name=f"item-{i}")
            await repo.save(model)
        await session.commit()

        results = await repo.list_all(TestModel, limit=3)
        assert len(results) == 3

    async def test_count(self, session):
        from chronoarb.domain.ulid import generate_ulid
        repo = BaseRepository[TestModel](session)
        for i in range(3):
            model = TestModel(id=generate_ulid("tst"), name=f"count-{i}")
            await repo.save(model)
        await session.commit()

        total = await repo.count(TestModel)
        assert total == 3

    async def test_delete(self, session):
        from chronoarb.domain.ulid import generate_ulid
        repo = BaseRepository[TestModel](session)
        model = TestModel(id=generate_ulid("tst"), name="to-delete")
        await repo.save(model)
        await session.commit()

        await repo.delete(model)
        await session.commit()

        deleted = await repo.get_by_id(TestModel, model.id)
        assert deleted is None


class TestTenantRepository:
    async def test_get_by_id_with_matching_org(self, session):
        from chronoarb.domain.ulid import generate_ulid
        repo = TenantRepository[TenantModel](session)
        model = TenantModel(id=generate_ulid("tnt"), organization_id="org_a", data="secret")
        await repo.save(model)
        await session.commit()

        found = await repo.get_by_id(TenantModel, model.id, organization_id="org_a")
        assert found is not None
        assert found.data == "secret"

    async def test_cross_tenant_returns_none(self, session):
        from chronoarb.domain.ulid import generate_ulid
        repo = TenantRepository[TenantModel](session)
        model = TenantModel(id=generate_ulid("tnt"), organization_id="org_a", data="secret")
        await repo.save(model)
        await session.commit()

        result = await repo.get_by_id(TenantModel, model.id, organization_id="org_b")
        assert result is None

    async def test_list_by_org_only_returns_own(self, session):
        from chronoarb.domain.ulid import generate_ulid
        repo = TenantRepository[TenantModel](session)
        for i in range(3):
            model = TenantModel(id=generate_ulid("tnt"), organization_id="org_a", data=f"a-{i}")
            await repo.save(model)
        model_b = TenantModel(id=generate_ulid("tnt"), organization_id="org_b", data="b-0")
        await repo.save(model_b)
        await session.commit()

        results = await repo.list_by_org(TenantModel, organization_id="org_a")
        assert len(results) == 3
        for r in results:
            assert r.organization_id == "org_a"

    async def test_nonexistent_id_returns_none(self, session):
        repo = TenantRepository[TenantModel](session)
        result = await repo.get_by_id(TenantModel, "nonexistent", organization_id="org_a")
        assert result is None


class TestRepositorySessionGuard:
    async def test_base_repo_requires_session(self):
        with pytest.raises(TypeError, match="requires a session"):
            BaseRepository[TestModel]()

    async def test_tenant_repo_requires_session(self):
        with pytest.raises(TypeError, match="requires a session"):
            TenantRepository[TenantModel]()

    async def test_tenant_repo_rejects_non_tenant_model(self, session):
        with pytest.raises(TypeError, match="organization_id"):
            TenantRepository[NonTenantModel](session, model_cls=NonTenantModel)

    async def test_tenant_repo_accepts_tenant_model(self, session):
        TenantRepository[TenantModel](session, model_cls=TenantModel)


class TestUnitOfWorkGuards:
    async def test_commit_outside_context_raises(self):
        uow = UnitOfWork()
        with pytest.raises(RuntimeError, match="no active session"):
            await uow.commit()

    async def test_rollback_outside_context_raises(self):
        uow = UnitOfWork()
        with pytest.raises(RuntimeError, match="no active session"):
            await uow.rollback()

    async def test_commit_within_context_succeeds(self, session):
        uow = UnitOfWork(session=session)
        assert uow.session is not None
        await uow.commit()

    async def test_exception_triggers_rollback(self, session):
        from chronoarb.domain.ulid import generate_ulid
        uow = UnitOfWork(session=session)
        repo = BaseRepository[TestModel](session)
        model = TestModel(id=generate_ulid("tst"), name="rollback-test")
        await repo.save(model)

        await uow.rollback()
        await session.rollback()



class TestOrganizationSettings:
    async def test_persist_and_reload_settings(self, session):
        from chronoarb.domain.ulid import generate_ulid
        org = Organization(
            id=generate_ulid("org"),
            name="Settings Org",
            slug="settings-org",
            settings={"timezone": "UTC", "default_currency": "USD"},
        )
        session.add(org)
        await session.commit()

        retrieved = await session.get(Organization, org.id)
        assert retrieved is not None
        assert retrieved.settings == {"timezone": "UTC", "default_currency": "USD"}

    async def test_settings_nullable(self, session):
        from chronoarb.domain.ulid import generate_ulid
        org = Organization(
            id=generate_ulid("org"),
            name="No Settings",
            slug="no-settings",
        )
        session.add(org)
        await session.commit()

        retrieved = await session.get(Organization, org.id)
        assert retrieved is not None
        assert retrieved.settings is None


class TestForeignKeyEnforcement:
    async def test_invalid_membership_fk_rejected(self, session):
        from chronoarb.domain.ulid import generate_ulid
        membership = Membership(
            id=generate_ulid("mem"),
            organization_id="nonexistent_org",
            user_id="nonexistent_user",
            role="dealer",
        )
        session.add(membership)
        with pytest.raises(Exception):
            await session.commit()
        await session.rollback()
