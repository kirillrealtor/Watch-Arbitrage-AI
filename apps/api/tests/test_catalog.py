from __future__ import annotations

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.infrastructure.models import Base
from apps.api.catalog.infrastructure.models import Brand, Source, Reference, Alias, WatchList, WatchListEntry
from apps.api.identity.infrastructure.models import Organization, User, Membership


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


class TestCatalogOrmParity:
    def test_brand_table_name(self):
        assert Brand.__tablename__ == "brands"

    def test_brand_unique_constraints(self):
        table = Brand.__table__
        assert table.c.name.unique is True
        assert table.c.slug.unique is True

    def test_source_table_name(self):
        assert Source.__tablename__ == "sources"

    def test_source_unique_constraints(self):
        table = Source.__table__
        assert table.c.source_key.unique is True

    def test_source_server_defaults(self):
        assert Source.__table__.c.is_enabled.server_default is not None

    def test_reference_table_name_is_reserved_word(self):
        assert Reference.__tablename__ == "references"

    def test_reference_unique_constraints(self):
        assert "uq_references_brand_ref" in [c.name for c in Reference.__table__.constraints]

    def test_reference_server_defaults(self):
        assert Reference.__table__.c.is_active.server_default is not None

    def test_alias_table_name(self):
        assert Alias.__tablename__ == "aliases"

    def test_alias_unique_constraints(self):
        assert "uq_aliases_text_source" in [c.name for c in Alias.__table__.constraints]

    def test_watch_list_table_name(self):
        assert WatchList.__tablename__ == "watch_lists"

    def test_watch_list_has_org_id(self):
        assert "organization_id" in WatchList.__table__.c

    def test_watch_list_entry_table_name(self):
        assert WatchListEntry.__tablename__ == "watch_list_entries"

    def test_watch_list_entry_unique_constraints(self):
        assert "uq_watch_list_entries_list_ref" in [c.name for c in WatchListEntry.__table__.constraints]


class TestPostgresqlDialectCompilation:
    def test_source_rate_policy_compiles_to_jsonb(self):
        from sqlalchemy.dialects.postgresql import dialect as pg_dialect
        from sqlalchemy.schema import CreateTable
        from sqlalchemy import MetaData, Table, Column

        m = MetaData()
        t = Table("t", m, Column("c", Source.__table__.c.rate_policy.type))
        sql = pg_dialect.ddl_compiler(pg_dialect(), CreateTable(t)).process(CreateTable(t))
        assert "JSONB" in sql

    def test_reference_attributes_compiles_to_jsonb(self):
        from sqlalchemy.dialects.postgresql import dialect as pg_dialect
        from sqlalchemy.schema import CreateTable
        from sqlalchemy import MetaData, Table, Column

        m = MetaData()
        t = Table("t", m, Column("c", Reference.__table__.c.attributes.type))
        sql = pg_dialect.ddl_compiler(pg_dialect(), CreateTable(t)).process(CreateTable(t))
        assert "JSONB" in sql


class TestIdentityRepositories:
    async def test_organization_crud(self, session):
        from chronoarb.domain.ulid import generate_ulid
        from apps.api.identity.infrastructure.repositories import OrganizationRepository

        repo = OrganizationRepository(session)
        org = Organization(id=generate_ulid("org"), name="Test Org", slug="test-org")
        await repo.save(org)
        await session.commit()

        found = await repo.get_by_id(Organization, org.id)
        assert found is not None
        assert found.name == "Test Org"

        found_by_slug = await repo.get_by_slug("test-org")
        assert found_by_slug is not None
        assert found_by_slug.id == org.id

    async def test_user_crud(self, session):
        from chronoarb.domain.ulid import generate_ulid
        from apps.api.identity.infrastructure.repositories import UserRepository

        repo = UserRepository(session)
        user = User(id=generate_ulid("usr"), cognito_sub="cog_1", email="a@b.com")
        await repo.save(user)
        await session.commit()

        found = await repo.get_by_cognito_sub("cog_1")
        assert found is not None
        assert found.email == "a@b.com"

    async def test_membership_lookup(self, session):
        from chronoarb.domain.ulid import generate_ulid
        from apps.api.identity.infrastructure.repositories import MembershipRepository

        org = Organization(id=generate_ulid("org"), name="O", slug="o")
        user = User(id=generate_ulid("usr"), cognito_sub="c1", email="x@y.com")
        session.add_all([org, user])
        await session.flush()

        mem = Membership(id=generate_ulid("mem"), organization_id=org.id, user_id=user.id, role="dealer")
        session.add(mem)
        await session.commit()

        repo = MembershipRepository(session)
        found = await repo.get_by_user_and_org(user.id, org.id)
        assert found is not None
        assert found.role == "dealer"

    async def test_membership_cross_tenant_returns_none(self, session):
        from chronoarb.domain.ulid import generate_ulid
        from apps.api.identity.infrastructure.repositories import MembershipRepository

        org1 = Organization(id=generate_ulid("org"), name="O1", slug="o1")
        org2 = Organization(id=generate_ulid("org"), name="O2", slug="o2")
        user = User(id=generate_ulid("usr"), cognito_sub="c1", email="x@y.com")
        session.add_all([org1, org2, user])
        await session.flush()

        mem = Membership(id=generate_ulid("mem"), organization_id=org1.id, user_id=user.id, role="dealer")
        session.add(mem)
        await session.commit()

        repo = MembershipRepository(session)
        wrong = await repo.get_by_user_and_org(user.id, org2.id)
        assert wrong is None


class TestCatalogRepositories:
    async def test_brand_lookup_by_name(self, session):
        from chronoarb.domain.ulid import generate_ulid
        from apps.api.catalog.infrastructure.repositories import BrandRepository

        brand = Brand(id=generate_ulid("brd"), name="Rolex", slug="rolex")
        session.add(brand)
        await session.commit()

        repo = BrandRepository(session)
        found = await repo.get_by_name("Rolex")
        assert found is not None

    async def test_reference_lookup_by_brand_and_code(self, session):
        from chronoarb.domain.ulid import generate_ulid
        from apps.api.catalog.infrastructure.repositories import ReferenceRepository

        brand = Brand(id=generate_ulid("brd"), name="Omega", slug="omega")
        ref = Reference(id=generate_ulid("ref"), brand_id=brand.id, ref_code="310.30.42")
        session.add_all([brand, ref])
        await session.commit()

        repo = ReferenceRepository(session)
        found = await repo.get_by_brand_and_ref_code(brand.id, "310.30.42")
        assert found is not None

    async def test_watchlist_tenant_isolation(self, session):
        from chronoarb.domain.ulid import generate_ulid
        from apps.api.catalog.infrastructure.repositories import WatchListRepository

        org_a = Organization(id=generate_ulid("org"), name="A", slug="a")
        org_b = Organization(id=generate_ulid("org"), name="B", slug="b")
        session.add_all([org_a, org_b])
        await session.flush()

        wl = WatchList(id=generate_ulid("wl"), organization_id=org_a.id, name="My List")
        session.add(wl)
        await session.commit()

        repo = WatchListRepository(session)
        results = await repo.list_by_org(WatchList, organization_id=org_a.id)
        assert len(results) == 1

        results_b = await repo.list_by_org(WatchList, organization_id=org_b.id)
        assert len(results_b) == 0


class TestForeignKeyEnforcementCatalog:
    async def test_watchlist_orphan_org_rejected(self, session):
        from chronoarb.domain.ulid import generate_ulid
        wl = WatchList(id=generate_ulid("wl"), organization_id="nonexistent", name="Bad")
        session.add(wl)
        with pytest.raises(Exception):
            await session.commit()
        await session.rollback()

    async def test_watchlist_entry_orphan_rejected(self, session):
        from chronoarb.domain.ulid import generate_ulid
        entry = WatchListEntry(id=generate_ulid("wle"), watch_list_id="fake", reference_id="fake")
        session.add(entry)
        with pytest.raises(Exception):
            await session.commit()
        await session.rollback()

    async def test_alias_orphan_rejected(self, session):
        from chronoarb.domain.ulid import generate_ulid
        alias = Alias(id=generate_ulid("als"), reference_id="fake", alias_text="test", source="manual")
        session.add(alias)
        with pytest.raises(Exception):
            await session.commit()
        await session.rollback()


class TestSchemas:
    def test_org_orm_to_response(self):
        from apps.api.identity.api.schemas import OrganizationResponse
        from chronoarb.domain.ulid import generate_ulid
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        org = Organization(id=generate_ulid("org"), name="T", slug="t",
                           created_at=now, updated_at=now)
        schema = OrganizationResponse.model_validate(org)
        assert schema.id == org.id
        assert schema.name == "T"

    def test_reference_no_internal_fields_exposed(self):
        from apps.api.catalog.api.schemas import ReferenceResponse
        fields = ReferenceResponse.model_fields.keys()
        assert "attributes" not in fields
        assert "__tablename__" not in fields
