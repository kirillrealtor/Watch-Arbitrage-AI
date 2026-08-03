# ChronoArb — Week 02 Domain Model & Repository Plan

**Plan type:** Sprint execution plan
**Dates:** Week 2 of 16 (Domain/Data Foundation)
**Date:** 2026-08-03T17:42:46+05:00
**Status:** Ready
**Prerequisite:** Batch 3 database completion (25 tables, 7 ENUMs, 12 indexes)
**Based on:** database-design.md, api-design.md, security-model.md

---

## 1. Objective

Create SQLAlchemy ORM models for all 25 database tables following the established conventions (Base, TimestampMixin, ULID TEXT PKs, NUMERIC for money), implement the repository layer with mandatory tenant isolation enforcement, and establish the domain service architecture. After Week 2, every data access path from API route through service through repository to database is established for identity, catalog, and listing read paths — with full tenant isolation verified in tests.

---

## 2. Implementation Scope

### In Scope

| Component | Scope |
|-----------|-------|
| SQLAlchemy ORM models | All 25 tables as Python classes using 2.0 Mapped[] annotations |
| Base repository | Abstract class with CRUD, pagination, cursor-based queries |
| Domain-specific repositories | identity, catalog, listings, valuation, opportunities, alerts, operations |
| Tenant isolation | Mandatory `organization_id` on every scoped repository method |
| Domain services | Identity (organization CRUD, membership), catalog (read), opportunities (feed) |
| Pydantic schemas | API-level DTOs for identity, catalog, and opportunity response types |
| Unit tests | Repositories, tenant isolation, cursor pagination |

### Out of Scope

| Component | Why Not |
|-----------|---------|
| Authentication middleware | Week 3-5 (Cognito integration) |
| Source adapters | Week 3-5 (requires source contracts) |
| Worker implementations | Week 6-8 (pipeline logic) |
| Stripe billing integration | Week 13 |
| Admin/operations endpoints | Week 9-10 (after auth) |
| Alert matching logic | Week 6-8 (requires valuation pipeline) |
| Full API routes | Week 3-5 (requires auth middleware) |

---

## 3. ORM Model Strategy

### 3.1 Conventions

All models follow these conventions established in Batch 3:

```python
from apps.api.infrastructure.models import Base, TimestampMixin

class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(sa.Text(), primary_key=True)
    name: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    slug: Mapped[str] = mapped_column(sa.Text(), unique=True, nullable=False)
    # ...
```

| Convention | Rule |
|-----------|------|
| Base class | `Base` from `apps.api.infrastructure.models` (DeclarativeBase) |
| Timestamp mixin | `TimestampMixin` for tables with `created_at`; tables with immutable records (valuations, raw_snapshots) use `created_at` directly |
| ULID PKs | `Mapped[str]` with `sa.Text()` — application generates ULIDs, no DB-level generation |
| Money columns | `Mapped[Decimal]` with `sa.Numeric(precision, scale)` — float prohibited |
| ENUM columns | `Mapped[str]` — storage is PostgreSQL ENUM, application reads as string |
| JSONB columns | `Mapped[dict]` with `postgresql.JSONB` — typed as dict at application level |
| Foreign keys | `Mapped[str]` with explicit `ForeignKey("table.column")` |
| Relationships | Declared with `relationship()` only where navigation is useful (not for all FKs) |
| `__tablename__` | Lowercase plural, matches migration table name |

### 3.2 Model Organization

```
apps/api/apps/api/
├── infrastructure/
│   └── models.py              # Base, TimestampMixin (already exists)
├── identity/
│   └── infrastructure/
│       └── models.py          # Organization, User, Membership
├── catalog/
│   └── infrastructure/
│       └── models.py          # Brand, Reference, Alias, WatchList, WatchListEntry, Source
├── listings/
│   └── infrastructure/
│       └── models.py          # RawSnapshot, ParsedListing, NormalizedListing,
│                              # DuplicateGroup, DuplicateGroupMember
├── valuation/
│   └── infrastructure/
│       └── models.py          # Valuation
├── opportunities/
│   └── infrastructure/
│       └── models.py          # Opportunity, OpportunityView
├── alerts/
│   └── infrastructure/
│       └── models.py          # AlertRule, AlertDelivery
├── feedback/
│   └── infrastructure/
│       └── models.py          # Feedback, TradeOutcome
├── billing/
│   └── infrastructure/
│       └── models.py          # Subscription
└── operations/
    └── infrastructure/
        └── models.py          # AuditEvent, OutboxEvent, FeatureFlag
```

**Rationale for per-module models:** Each backend module owns its SQLAlchemy models. This prevents cross-module import coupling (ADR-0007). The `Base` from `infrastructure/models.py` is the only shared dependency.

### 3.3 Model ↔ Migration Sync

Models are validated against the database schema by:
1. Running `alembic upgrade head` to create all tables
2. Creating a test that instantiates each model and verifies `Base.metadata.create_all()` does not produce schema drift from the migration-defined DDL

**No autogenerate is enabled.** Migrations remain hand-written per ADR-0008. Models reflect the current migration state.

### 3.4 Immutable Records

Three tables contain immutable records per ADR-0001 D10:
- `valuations` — created once, never updated
- `opportunities` — new material version = new row, old rows preserved
- `raw_snapshots` — created once, never updated

These models do NOT include `TimestampMixin` (which adds `updated_at`). They define `created_at` directly.

---

## 4. Repository Architecture

### 4.1 Repository Base Class

```python
# apps/api/apps/api/infrastructure/repository.py

from sqlalchemy.ext.asyncio import AsyncSession

class BaseRepository[Model]:
    def __init__(self, session: AsyncSession): ...

    async def get_by_id(self, id: str) -> Model | None: ...
    async def list_all(self, limit: int = 50, cursor: str | None = None) -> list[Model]: ...
    async def count(self) -> int: ...
    async def save(self, model: Model) -> Model: ...
    async def delete(self, model: Model) -> None: ...
```

### 4.2 Tenant-Scoped Repository

For tables with `organization_id`:

```python
class TenantRepository[Model](BaseRepository[Model]):
    async def get_by_id(self, id: str, organization_id: str) -> Model | None:
        # Always filters by organization_id — cross-tenant returns None
        ...

    async def list_by_org(self, organization_id: str, limit: int = 50, cursor: str | None = None) -> list[Model]:
        ...
```

**Pattern:** Every method on a tenant-scoped repository requires `organization_id`. No method allows querying across tenants. If `organization_id` is omitted, the method raises `TypeError` at call time.

### 4.3 Repository Inventory

| Domain | Repository | Base Class | Tables | Tenant-Scoped? |
|--------|-----------|------------|--------|---------------|
| Identity | `OrganizationRepository` | BaseRepository | organizations | No (global identity) |
| Identity | `UserRepository` | BaseRepository | users | No (global identity) |
| Identity | `MembershipRepository` | TenantRepository | memberships | Yes |
| Catalog | `BrandRepository` | BaseRepository | brands | No |
| Catalog | `ReferenceRepository` | BaseRepository | references | No |
| Catalog | `WatchListRepository` | TenantRepository | watch_lists, watch_list_entries | Yes |
| Catalog | `SourceRepository` | BaseRepository | sources | No (platform ops) |
| Listings | `ListingRepository` | BaseRepository | raw_snapshots, parsed_listings, normalized_listings | No (global data) |
| Listings | `DuplicateRepository` | BaseRepository | duplicate_groups, duplicate_group_members | No |
| Valuation | `ValuationRepository` | BaseRepository | valuations | No (global analysis) |
| Opportunities | `OpportunityRepository` | TenantRepository | opportunities, opportunity_views | Yes |
| Alerts | `AlertRuleRepository` | TenantRepository | alert_rules | Yes |
| Alerts | `AlertDeliveryRepository` | TenantRepository | alert_deliveries | Yes |
| Feedback | `FeedbackRepository` | TenantRepository | feedbacks | Yes |
| Feedback | `TradeOutcomeRepository` | TenantRepository | trade_outcomes | Yes |
| Billing | `SubscriptionRepository` | TenantRepository | subscriptions | Yes |
| Operations | `AuditEventRepository` | BaseRepository | audit_events | No (nullable org) |
| Operations | `OutboxEventRepository` | BaseRepository | outbox_events | No |
| Operations | `FeatureFlagRepository` | BaseRepository | feature_flags | No |

### 4.4 Cursor Pagination Convention

Repositories use cursor-based pagination with the `next_cursor` pattern from `api-design.md` §5:

```python
async def list_by_org(
    self,
    organization_id: str,
    limit: int = 50,
    cursor: str | None = None,
) -> tuple[list[Opportunity], str | None]:
    query = (
        select(Opportunity)
        .where(Opportunity.organization_id == organization_id)
        .order_by(Opportunity.published_at.desc(), Opportunity.id)
    )
    if cursor:
        cursor_pub_at, cursor_id = decode_cursor(cursor)
        query = query.where(
            or_(
                Opportunity.published_at < cursor_pub_at,
                and_(Opportunity.published_at == cursor_pub_at, Opportunity.id < cursor_id),
            )
        )
    rows = (await self.session.execute(query.limit(limit + 1))).scalars().all()
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = encode_cursor(items[-1].published_at, items[-1].id) if has_more else None
    return items, next_cursor
```

---

## 5. Application Service Boundaries

### 5.1 Service Architecture

```
API Route (thin — validates, calls service, maps response)
   │
   ▼
Application Service (orchestrates use case, manages transactions)
   │
   ├──► Repository (data access, tenant-scoped)
   ├──► Domain objects (Money, policies, formulas — from packages/domain-python)
   └──► Outbox (writes events in same transaction)
   │
   ▼
Pydantic Schema (maps domain output to API response)
```

### Layer Responsibilities

| Layer | Directory | Contents | Dependencies |
|-------|-----------|----------|-------------|
| **API** | `api/` | Routes, middleware, Pydantic request/response schemas | Application services |
| **Application** | `application/` | Service classes, commands, queries, transaction orchestration | Repositories, domain objects, outbox |
| **Domain** | `domain/` | Pure business rules, policies, formulas — no I/O, no framework deps | packages/domain-python only |
| **Infrastructure** | `infrastructure/` | SQLAlchemy models, repositories, database sessions, external gateways | SQLAlchemy, asyncpg/aiosqlite |

Services live in each module's `application/` directory. They call repositories and coordinate transactions — they depend on infrastructure, so they belong in the application layer. The `domain/` directory is reserved for pure business logic with zero infrastructure dependencies.

### 5.2 Week 2 Services

| Service | Module | Responsibilities |
|---------|--------|----------------|
| `OrganizationService` | identity | Create org, update settings, list members, invite members |
| `MembershipService` | identity | Assign role, remove member, validate membership |
| `CatalogService` | catalog | List references, get reference detail, list brands |
| `WatchListService` | catalog | Create/update/delete watch lists, add/remove entries |
| `OpportunityFeedService` | opportunities | Ranked feed query with cursor pagination, detail view |
| `AlertRuleService` | alerts | CRUD for alert rules, validation |

### 5.3 Transaction Boundaries

```python
# Service method pattern
async def create_organization(self, cmd: CreateOrganizationCommand) -> Organization:
    async with self.uow:  # Unit of Work = session + outbox
        org = Organization(id=generate_ulid("org"), name=cmd.name, slug=cmd.slug)
        await self.org_repo.save(org)

        event = OutboxEvent(
            id=generate_ulid("out"),
            event_name="organization.created",
            event_version="1.0",
            payload={"organization_id": org.id, "name": org.name},
            status="pending",
        )
        await self.outbox_repo.save(event)

        await self.uow.commit()  # Both org and event committed atomically
    return org
```

**Rule:** Every state-changing operation writes its outbox event in the same transaction. No external call (queue publish, webhook, notification) happens inside the transaction boundary.

---

## 6. Tenant Isolation Enforcement

### 6.1 Pattern

```python
# ✅ Correct: organization_id is mandatory
async def get_opportunity(self, opp_id: str, organization_id: str) -> Opportunity | None:
    return await self.session.get(Opportunity, (opp_id, organization_id))

# ❌ Wrong: organization_id is optional
async def get_opportunity(self, opp_id: str, organization_id: str | None = None):
    ...

# ❌ Wrong: no organization_id at all
async def get_opportunity(self, opp_id: str):
    ...
```

### 6.2 Cross-Tenant Protection

- Tenant repository methods that receive an `organization_id` filter by it in every query
- If the row exists but belongs to a different organization, return `None` (not 403)
- This prevents information leakage — attackers cannot distinguish "doesn't exist" from "exists but not yours"
- Unit tests must verify: query with wrong `organization_id` returns `None` even when the row exists

### 6.3 Global Data Access

Non-tenant tables (sources, references, normalized_listings, valuations) are accessed through `BaseRepository` — no `organization_id` parameter. These contain shared pipeline data visible to all tenants.

---

## 7. Mapping Between Database and Domain Objects

### 7.1 Layer Separation

| Layer | Object Type | Purpose | Example |
|-------|------------|---------|---------|
| Database | SQLAlchemy Model | Persistence | `OrganizationModel` |
| Domain | Python dataclass/class | Business logic | `Organization` (from packages/domain-python) |
| API | Pydantic schema | Request/response serialization | `OrganizationResponse` |

### 7.2 Mapping Strategy

**Week 2:** Direct mapping. SQLAlchemy models ARE the domain objects for simple cases (Organizations, Brands, References — read-only, no complex business logic). For money-bearing entities, the `Money` value object from `packages/domain-python` is used for financial calculations but the ORM model stores raw `Decimal` columns.

```python
# Repository returns ORM model
org_model = await org_repo.get_by_id(org_id)

# Service maps to domain if needed, or exposes model directly
# (for simple reads where model == domain for now)
return OrganizationResponse(
    id=org_model.id,
    name=org_model.name,
    slug=org_model.slug,
    created_at=org_model.created_at,
)
```

**Week 3-5:** Full DTO mapping when complex business logic (valuation, alert matching) is implemented. Services return domain objects with computed properties. API routes map domain objects to Pydantic responses.

### 7.3 Money Mapping

```python
# ORM model stores raw Decimal
class ValuationModel(Base):
    expected_net_profit: Mapped[Decimal] = mapped_column(sa.Numeric(18, 2))

# Service maps to domain Money object for calculations
valuation = await valuation_repo.get_by_id(val_id)
profit = Money(amount=valuation.expected_net_profit, currency=valuation.exit_price_currency)
# ... domain calculations using Money arithmetic ...

# API response returns string representation
class ValuationResponse(BaseModel):
    expected_net_profit: str  # "675.00" — string to preserve precision
    exit_price_currency: str  # "USD"
```

---

## 8. Testing Strategy

### 8.1 Test Layers

| Layer | Tool | Scope |
|-------|------|-------|
| Model unit tests | pytest | Instantiation, defaults, constraint behavior |
| Repository unit tests | pytest + async session | CRUD, pagination, tenant isolation, cursor logic |
| Service unit tests | pytest + mock repositories | Business logic, validation, event publishing |
| Integration tests | pytest + real SQLite/PostgreSQL | End-to-end: route → service → repo → DB |

### 8.2 Tenant Isolation Tests (Mandatory)

Every tenant-scoped repository must have these tests:

```python
async def test_cross_tenant_access_returns_none(session):
    # Create org A with opportunity 1
    repo = OpportunityRepository(session)
    opp = await create_test_opportunity(session, org_id="org_a")

    # Query with org B's ID
    result = await repo.get_by_id(opp.id, organization_id="org_b")
    assert result is None

async def test_list_by_org_only_returns_own_opportunities(session):
    repo = OpportunityRepository(session)
    await create_test_opportunity(session, org_id="org_a")
    await create_test_opportunity(session, org_id="org_b")

    results = await repo.list_by_org(organization_id="org_a", limit=50)
    assert len(results) == 1
    assert results[0].organization_id == "org_a"
```

### 8.3 Test Fixtures

```python
# conftest.py
@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine)() as session:
        yield session
    await engine.dispose()
```

---

## 9. Workstreams

### Week 2 Day-by-Day

**Day 1 — Infrastructure + Identity Models**
- Write `BaseRepository` and `TenantRepository` base classes
- Write SQLAlchemy models for identity (Organization, User, Membership)
- Write `OrganizationRepository`, `UserRepository`, `MembershipRepository`
- Write tenant isolation tests for membership queries

**Day 2 — Catalog Models + Read Repositories**
- Write SQLAlchemy models for catalog (Brand, Reference, Alias, WatchList, WatchListEntry, Source)
- Write read-only repositories
- Write `WatchListRepository` with tenant scoping
- Write pagination tests

**Day 3 — Pipeline Data Models**
- Write SQLAlchemy models for listings (RawSnapshot, ParsedListing, NormalizedListing)
- Write SQLAlchemy models for duplicates (DuplicateGroup, DuplicateGroupMember)
- Write SQLAlchemy models for valuation (Valuation)
- Write read-only repositories

**Day 4 — Business Process Models + Tenant Repositories**
- Write SQLAlchemy models for opportunities (Opportunity, OpportunityView)
- Write `OpportunityRepository` with cursor pagination and tenant scoping
- Write SQLAlchemy models for alerts (AlertRule, AlertDelivery)
- Write `AlertRuleRepository`, `AlertDeliveryRepository`
- Write feedback models (Feedback, TradeOutcome)
- Write billing/operations models (Subscription, AuditEvent, OutboxEvent, FeatureFlag)

**Day 5 — Services + Integration**
- Write `OrganizationService`, `MembershipService`
- Write `CatalogService`, `WatchListService`
- Write `OpportunityFeedService` with cursor pagination
- Integration tests: full chain from service → repo → DB
- Tenant isolation integration tests

---

## 10. File Manifest

```
apps/api/apps/api/
├── infrastructure/
│   ├── models.py              # Base, TimestampMixin (already exists)
│   └── repository.py          # BaseRepository, TenantRepository [NEW]
├── identity/
│   ├── infrastructure/
│   │   └── models.py          # Organization, User, Membership [NEW]
│   ├── application/
│   │   └── services.py        # OrganizationService, MembershipService [NEW]
│   └── api/
│       └── schemas.py         # OrganizationResponse, MembershipResponse, UserResponse [NEW]
├── catalog/
│   ├── infrastructure/
│   │   └── models.py          # Brand, Reference, Alias, WatchList, WatchListEntry, Source [NEW]
│   ├── application/
│   │   └── services.py        # CatalogService, WatchListService [NEW]
│   └── api/
│       └── schemas.py         # ReferenceResponse, BrandResponse, WatchListResponse [NEW]
├── listings/
│   └── infrastructure/
│       └── models.py          # RawSnapshot, ParsedListing, NormalizedListing,
│                              # DuplicateGroup, DuplicateGroupMember [NEW]
├── valuation/
│   └── infrastructure/
│       └── models.py          # Valuation [NEW]
├── opportunities/
│   ├── infrastructure/
│   │   └── models.py          # Opportunity, OpportunityView [NEW]
│   ├── application/
│   │   └── services.py        # OpportunityFeedService [NEW]
│   └── api/
│       └── schemas.py         # OpportunityResponse, OpportunityFeedResponse [NEW]
├── alerts/
│   ├── infrastructure/
│   │   └── models.py          # AlertRule, AlertDelivery [NEW]
│   ├── application/
│   │   └── services.py        # AlertRuleService [NEW]
│   └── api/
│       └── schemas.py         # AlertRuleResponse, AlertDeliveryResponse [NEW]
├── feedback/
│   └── infrastructure/
│       └── models.py          # Feedback, TradeOutcome [NEW]
├── billing/
│   └── infrastructure/
│       └── models.py          # Subscription [NEW]
└── operations/
    └── infrastructure/
        └── models.py          # AuditEvent, OutboxEvent, FeatureFlag [NEW]

apps/api/tests/
├── conftest.py                # Database session fixtures [NEW]
├── test_identity_repository.py  [NEW]
├── test_catalog_repository.py   [NEW]
├── test_opportunity_repository.py [NEW]
├── test_alert_repository.py     [NEW]
├── test_tenant_isolation.py     [NEW]
├── test_cursor_pagination.py    [NEW]
└── test_services.py             [NEW]
```

---

## 11. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-01 | All 25 tables have SQLAlchemy ORM models | `python -c "from apps.api.{module}.infrastructure.models import *"` for all 10 modules |
| AC-02 | `BaseRepository` with CRUD operations | `test_base_repository` passes |
| AC-03 | `TenantRepository` enforces organization_id | `test_tenant_isolation.py` passes — cross-tenant access returns None |
| AC-04 | Cursor pagination works for opportunities | `test_cursor_pagination.py` passes — no duplicates, no gaps |
| AC-05 | Money columns use Decimal with correct precision | Models use `Mapped[Decimal]` with `sa.Numeric(precision, scale)` matching migration DDL |
| AC-06 | ULID PKs are TEXT | No `UUID` or `Integer` PK columns — all `Mapped[str]` with `sa.Text()` |
| AC-07 | Immutable tables lack `updated_at` | `valuations`, `raw_snapshots`, `opportunities` models have `created_at` but no `updated_at` |
| AC-08 | Models validate against migration schema | `Base.metadata.create_all()` does not produce extra tables or columns vs migration DDL |
| AC-09 | Services orchestrate repositories correctly | `test_services.py` passes — create org, invite member, query feed |
| AC-10 | No cross-package model imports | Import-linter passes with no new forbidden imports |

---

## 12. ADR Compliance

| ADR | Requirement | Week 2 Implementation |
|-----|-------------|----------------------|
| ADR-0001 D3 | Decimal for money | All money columns use `Mapped[Decimal]` with `sa.Numeric` |
| ADR-0001 D4 | ULID TEXT PKs | All PKs: `Mapped[str] = mapped_column(sa.Text(), primary_key=True)` |
| ADR-0001 D7 | Tenant isolation | `TenantRepository` base class enforces `organization_id` on every method |
| ADR-0001 D9 | Source adapter isolation | Not applicable (models are not source-specific) |
| ADR-0007 | Package dependency direction | No cross-module model imports; all models import only from `infrastructure/models.py` |
