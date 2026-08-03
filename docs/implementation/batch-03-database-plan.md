# ChronoArb — Batch 03 Database Foundation Plan

**Plan type:** Sprint execution plan
**Batch:** 3 of 8 — Database Foundation
**Date:** 2026-08-03
**Status:** Ready for implementation
**Prerequisites:** Batch 2 closure approved (READY FOR BATCH 3)

---

## 1. Objective

Wire the FastAPI application to a real PostgreSQL database via SQLAlchemy async engine, initialize Alembic, and create the initial migration defining all 25 tables with indexes per `database-design.md` and incorporating all ADR-mandated corrections (ADR-0002, ADR-0004, ADR-0005). After this batch, `alembic upgrade head` creates a complete schema and `GET /ready` returns real database connectivity.

---

## 2. Scope

### In Scope

| Component | Details |
|-----------|---------|
| PostgreSQL instance | Docker container (postgres:18 or nearest available) |
| Database creation | `createdb chronoarb` with UTF-8, UTC |
| Alembic initialization | `alembic init` with async template, DATABASE_URL from settings |
| Initial migration | `001-003_*.py` — 25 tables, ~20 indexes, all constraints |
| SQLAlchemy engine | AsyncEngine from DATABASE_URL |
| Session management | async_sessionmaker with get_db dependency |
| Base model conventions | DeclarativeBase, TimestampMixin, ULID primary key type |
| ENUM types | PostgreSQL native ENUMs for role, state, status, decision, delivery_status, outbox_status |
| ADR-0002 compliance | alert_deliveries has organization_id + material_version; no composite UNIQUE |
| ADR-0004 compliance | normalized_listings has observation_at TIMESTAMPTZ NOT NULL |
| ADR-0005 compliance | normalized_listings has fx_source TEXT NOT NULL, fx_date DATE NOT NULL |
| ALL table definitions | Exact column types, constraints, foreign keys, defaults from database-design.md §2 |
| ALL indexes | 16 indexes from database-design.md §3 |
| Ready endpoint upgrade | Wire get_db_status to real async SQLAlchemy connection check |
| Test updates | Health tests adjusted for real DB (pytest fixtures, test database) |

### Out of Scope

| Component | Why Not |
|-----------|---------|
| Repository implementations | Week 3-5 — no tenant-scoped queries yet |
| Application services | Week 3-5 — no use-case orchestration yet |
| Data seed scripts | Week 3-5 — catalog data loaded when references are defined |
| Expand/contract migrations | Not applicable — this is the first migration |
| Read replicas | MVP — single RDS instance |
| Table partitioning | Per database-design.md §6 — no partitioning at MVP |
| Redis connection | Batch 7 — Docker + Infrastructure |
| SQS integration | Batch 4 (Worker) — not yet needed |
| Alembic autogenerate | Not used for initial migration — this migration is hand-written per the execution batches plan |
| Model ↔ Migration sync validation | Week 2+ — not yet needed; SQLAlchemy models not created until application code needs them |

---

## 3. Tasks

### Task Summary

| ID | Task | Size | Dependencies |
|----|------|------|-------------|
| DB-01 | Start PostgreSQL Docker container | XS | Docker installed |
| DB-02 | Create database and verify connectivity | XS | DB-01 |
| DB-03 | Initialize Alembic with async configuration | Small | DB-02, WF-11 (B2) |
| DB-04 | Create SQLAlchemy engine, session factory, get_db dependency | Small | DB-02, WF-21 (B2) |
| DB-05 | Create base model conventions (DeclarativeBase, mixins) | Small | DB-04 |
| DB-06 | Write initial migration — tables 1-8 (identity, catalog, sources, listings) | Medium | DB-03 |
| DB-07 | Write initial migration — tables 9-16 (normalization, duplicates, valuation, opportunities) | Medium | DB-03 |
| DB-08 | Write initial migration — tables 17-22 (alerts, feedback, billing, operations, audit, feature flags) | Medium | DB-03 |
| DB-09 | Write initial migration — all indexes | Small | DB-06, DB-07, DB-08 |
| DB-10 | Upgrade real database (dockerized PostgreSQL) | XS | DB-09 |
| DB-11 | Verify schema: 25 tables, all constraints, all indexes | XS | DB-10 |
| DB-12 | Upgrade /ready endpoint to real DB check | XS | DB-04, DB-10 |
| DB-13 | Write integration tests for database connectivity | Small | DB-04, DB-10 |
| DB-14 | Downgrade and re-upgrade migration | XS | DB-10 |
| DB-15 | Update test fixtures for database-dependent tests | Small | DB-04 |

**Note:** DB-06, DB-07, and DB-08 are Medium tasks (90-180 minutes each) because they involve careful transcription of 22 table definitions with 100+ columns, constraints, FKs, and ENUM types. They are separated into three migration files for manageable size and reviewability. DB-09 depends on all three and is the index-only migration.

---

### DB-01: Start PostgreSQL Docker Container

- **Size:** XS
- **Files affected:** None (infrastructure)
- **Dependencies:** Docker installed on host
- **Acceptance criteria:**
  - PostgreSQL container running on port 5432
  - `docker ps` shows `chronoarb-pg` container with status "Up"
  - Version is PostgreSQL 17
- **Verification:**
  ```bash
  docker run -d --name chronoarb-pg -p 5432:5432 \
    -e POSTGRES_PASSWORD=chronoarb \
    -e POSTGRES_DB=chronoarb \
    postgres:17
  docker ps --filter name=chronoarb-pg
  psql -h localhost -U postgres -c "SELECT version();"
  ```
- **Rollback:** `docker stop chronoarb-pg && docker rm chronoarb-pg`
- **Risk:** `postgres:17` is mature with stable ecosystem support across SQLAlchemy, Alembic, and asyncpg. No version risk.

---

### DB-02: Create Database and Verify Connectivity

- **Size:** XS
- **Files affected:** None (database operation)
- **Dependencies:** DB-01
- **Acceptance criteria:**
  - Database `chronoarb` exists
  - Connection succeeds with `postgres:chronoarb` credentials
  - Database uses UTF-8 encoding
- **Verification:**
  ```bash
  psql -h localhost -U postgres -c "CREATE DATABASE chronoarb ENCODING 'UTF8';"
  psql -h localhost -U postgres -d chronoarb -c "SELECT current_database(), current_setting('TIMEZONE');"
  ```
- **Rollback:** `psql -h localhost -U postgres -c "DROP DATABASE chronoarb;"`

---

### DB-03: Initialize Alembic with Async Configuration

- **Size:** Small
- **Files affected:** `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`
- **Dependencies:** DB-02, WF-11 (B2 — Alembic installed via apps/api[dev])
- **Acceptance criteria:**
  - `alembic.ini` reads `DATABASE_URL` from settings (not hardcoded)
  - `env.py` uses async SQLAlchemy engine
  - `env.py` prepares for future SQLAlchemy metadata integration (`target_metadata` is set to `None` initially)
- Migrations are hand-written via Alembic's `op.create_table()` — no autogenerate
- Autogenerate will be enabled when ORM models are created (Week 3-5)
  - `script.py.mako` has revision template with `create date`, `Revision ID`, `Revises`, `Create Date`
  - `alembic current` reports no migrations applied (empty database)
- **Verification:**
  ```bash
  alembic init -t async alembic
  # Edit alembic.ini: sqlalchemy.url = (read from env, not hardcoded)
  # Edit env.py: import async engine, configure run_migrations_online
  alembic current
  # → No current revision — database is empty
  ```
- **Files created:**
  - `alembic.ini` — Alembic config, `sqlalchemy.url` reads `DATABASE_URL` env var
  - `alembic/env.py` — Async engine, `target_metadata` from DeclarativeBase, `run_migrations_online`
  - `alembic/script.py.mako` — Migration file template
  - `alembic/versions/` — Empty directory for migrations
- **Rollback:** `rm -rf alembic/ alembic.ini`

---

### DB-04: Create SQLAlchemy Engine, Session Factory, get_db Dependency

- **Size:** Small
- **Files affected:** `apps/api/apps/api/infrastructure/database.py`, `apps/api/apps/api/settings.py`, `apps/api/apps/api/deps.py`
- **Dependencies:** DB-02, WF-21 (B2 — FastAPI app exists), WF-23 (B2 placeholder — done from B2 scope)
- **Acceptance criteria:**
  - `create_async_engine(settings.database_url)` returns a configured `AsyncEngine`
  - `async_sessionmaker` configured with `expire_on_commit=False`
  - `get_db` async generator yields a session and closes it
  - Engine echo is controlled by `settings.debug`
  - Connection pool: min 5, max 20 (sane defaults for local dev)
- **Verification:**
  ```bash
  python -c "
  from apps.api.settings import settings
  from apps.api.infrastructure.database import engine, async_session
  print(engine.url)
  "
  ```
- **Files created/modified:**
  - `apps/api/apps/api/infrastructure/__init__.py` (create if missing)
  - `apps/api/apps/api/infrastructure/database.py` — AsyncEngine, sessionmaker, get_db
  - `apps/api/apps/api/deps.py` — Updated get_db_status to use real engine connection
- **Rollback:** Revert `deps.py` to placeholder; remove `database.py`

---

### DB-05: Create Base Model Conventions

- **Size:** Small
- **Files affected:** `apps/api/apps/api/infrastructure/models.py`
- **Dependencies:** DB-04
- **Acceptance criteria:**
  - `Base` = `DeclarativeBase` with `registry()` for metadata
  - `TimestampMixin` with `created_at: Mapped[datetime]` and optional `updated_at: Mapped[datetime | None]`
  - ULID primary key type is `TEXT` (not UUID — ULIDs are stored as text)
  - All timestamps use `TIMESTAMPTZ` with `server_default=func.now()`
  - `created_at` defaults to `NOW()` at the database level
  - Mixins are composable: a model can inherit both `TimestampMixin` and table definitions
- **Verification:**
  ```bash
  python -c "
  from apps.api.infrastructure.models import Base, TimestampMixin
  print('Base metadata:', Base.metadata)
  print('TimestampMixin fields:', TimestampMixin.__annotations__)
  "
  ```
- **Files created:**
  - `apps/api/apps/api/infrastructure/models.py` — Base, TimestampMixin, convention configurations
- **Rollback:** Remove `models.py`; no migration depends on models (migrations are hand-written SQL)

---

### DB-06: Initial Migration — Tables 1-8

- **Size:** Medium
- **Files affected:** `alembic/versions/001_identity_and_catalog.py`
- **Dependencies:** DB-03
- **Tables covered:**
  1. `organizations`
  2. `users`
  3. `memberships` (ENUM: `membership_role`)
  4. `brands`
  5. `references`
  6. `aliases`
  7. `watch_lists`
  8. `watch_list_entries`
  9. `sources`
- **Acceptance criteria:**
  - All 9 tables created with correct column types per database-design.md §2.1-2.3
  - Primary keys: `TEXT PRIMARY KEY` (ULID)
  - Timestamps: `TIMESTAMPTZ NOT NULL DEFAULT NOW()`
  - Foreign keys: `REFERENCES organizations(id)`, `REFERENCES users(id)`, `REFERENCES brands(id)`, `REFERENCES references(id)`, `REFERENCES watch_lists(id)`
  - UNIQUE constraints: `memberships(user_id, org_id)`, `brands(slug)`, `references(brand_id, ref_code)`, `aliases(alias_text, source)`, `watch_list_entries(watch_list_id, reference_id)`, `sources(source_key)`
  - ENUM: `membership_role` with values `owner`, `admin`, `dealer`, `viewer`
  - JSONB: `organizations.settings`, `references.attributes`, `sources.rate_policy`
  - BOOLEAN: `references.is_active DEFAULT true`, `sources.is_enabled DEFAULT false`
  - `slug` fields have `UNIQUE NOT NULL`
  - `cognito_sub` and `email` have `UNIQUE NOT NULL`
  - Downgrade drops all 9 tables in reverse creation order
- **Verification:**
  ```bash
  alembic upgrade head  # Creates first 9 tables
  psql -d chronoarb -c "\dt" | wc -l  # 9 tables + header
  psql -d chronoarb -c "\d organizations"
  psql -d chronoarb -c "\d memberships"
  ```
- **Rollback:** `alembic downgrade -1` drops all 9 tables

---

### DB-07: Initial Migration — Tables 10-17

- **Size:** Medium
- **Files affected:** `alembic/versions/002_listings_and_valuation.py`
- **Dependencies:** DB-03 (independent of DB-06 — can run in parallel)
- **Tables covered:**
  10. `raw_snapshots`
  11. `parsed_listings`
  12. `normalized_listings` (ADR-0004: `observation_at`, ADR-0005: `fx_source`, `fx_date`)
  13. `duplicate_groups`
  14. `duplicate_group_members`
  15. `valuations`
  16. `opportunities` (ENUM: `opportunity_state`)
  17. `opportunity_views`
- **ADR compliance checklist:**
  - ADR-0004: `normalized_listings.observation_at TIMESTAMPTZ NOT NULL`
  - ADR-0005: `normalized_listings.fx_source TEXT NOT NULL`, `normalized_listings.fx_date DATE NOT NULL`
  - `normalized_listings.fx_rate NUMERIC(18,8) NOT NULL`
  - `normalized_listings.status` ENUM: `active`, `quarantined`, `suppressed`, `stale`
  - `opportunities.state` ENUM: `published`, `dismissed`, `contacted`, `purchased`, `expired`
  - `opportunities` UNIQUE: `(organization_id, listing_id, material_version)`
  - `raw_snapshots` UNIQUE: `(source_id, external_id, adapter_version, checksum)`
  - Money columns: `NUMERIC(18,2)` for prices, `NUMERIC(10,6)` for ROI, `NUMERIC(5,4)` for match_confidence/confidence
  - `listing_price` and `price_currency` on parsed_listings
  - `normalized_price` and `normalized_currency` on normalized_listings
- **Verification:**
  ```bash
  alembic upgrade head  # Creates tables 10-17 (after DB-06)
  psql -d chronoarb -c "\d normalized_listings"  # Verify observation_at, fx_source, fx_date
  psql -d chronoarb -c "\d valuations"           # Verify NUMERIC types
  psql -d chronoarb -c "\d opportunities"        # Verify state enum
  ```
- **Rollback:** `alembic downgrade -1` drops all 8 tables

---

### DB-08: Initial Migration — Tables 18-25

- **Size:** Medium
- **Files affected:** `alembic/versions/003_alerts_and_operations.py`
- **Dependencies:** DB-03 (independent of DB-06, DB-07 — can run in parallel)
- **Tables covered:**
  18. `alert_rules`
  19. `alert_deliveries` (ADR-0002: `organization_id`, `material_version`, NO composite UNIQUE)
  20. `feedbacks` (ENUM: `feedback_decision`)
  21. `trade_outcomes`
  22. `subscriptions` (ENUM: `subscription_status`)
  23. `audit_events`
  24. `outbox_events` (ENUM: `outbox_event_status`)
  25. `feature_flags`
- **ADR-0002 compliance checklist:**
  - `alert_deliveries.organization_id TEXT NOT NULL REFERENCES organizations(id)` ✓
  - `alert_deliveries.material_version INT NOT NULL` ✓
  - NO composite UNIQUE on `(rule_id, user_id, opportunity_id, channel, material_version)` ✓
  - `alert_deliveries.idempotency_key TEXT UNIQUE NOT NULL` provides uniqueness guarantee ✓
- **Additional ENUMs:**
  - `alert_deliveries.delivery_status`: `pending`, `sent`, `failed`, `suppressed`
  - `feedbacks.decision`: `purchased`, `contacted`, `dismissed`
  - `subscriptions.status`: `trialing`, `active`, `past_due`, `canceled`, `unpaid`
  - `outbox_events.status`: `pending`, `published`, `failed`
- **Verification:**
  ```bash
   alembic upgrade head  # Creates tables 18-25 (after DB-06, DB-07)
  psql -d chronoarb -c "\d alert_deliveries"    # Verify org_id + material_version columns
  psql -d chronoarb -c "SELECT typname FROM pg_type WHERE typname LIKE '%_%';"  # List all ENUMs
  ```
- **Rollback:** `alembic downgrade -1` drops all 8 tables

---

### DB-09: Initial Migration — All Indexes

- **Size:** Small
- **Files affected:** `alembic/versions/004_indexes.py`
- **Dependencies:** DB-06, DB-07, DB-08 (all tables must exist before indexes)
- **Indexes created:**
  1. `idx_memberships_org_user` — `ON memberships(organization_id, user_id)`
  2. `idx_opportunities_org_state` — `ON opportunities(organization_id, state, published_at DESC)`
  3. `idx_alert_rules_org` — `ON alert_rules(organization_id, is_enabled)`
  4. `idx_feedbacks_org_opp` — `ON feedbacks(organization_id, opportunity_id)`
  5. `idx_opportunities_published` — `ON opportunities(state, published_at DESC) WHERE state = 'published'`
  6. `idx_normalized_listings_ref` — `ON normalized_listings(reference_id, status, created_at DESC)`
  7. `idx_normalized_listings_active` — `ON normalized_listings(status, reference_id) WHERE status = 'active'`
  8. `idx_alert_deliveries_idem` — `ON alert_deliveries(idempotency_key)` (per ADR-0002)
  9. `idx_alert_deliveries_org_user` — `ON alert_deliveries(organization_id, user_id, created_at DESC)` (per ADR-0002)
  10. `idx_alert_deliveries_opp` — `ON alert_deliveries(opportunity_id, material_version)` (per ADR-0002)
  11. `idx_feedbacks_idem` — `ON feedbacks(idempotency_key)`
  12. `idx_trade_outcomes_idem` — `ON trade_outcomes(idempotency_key)`
  13. `idx_outbox_pending` — `ON outbox_events(status, created_at) WHERE status = 'pending'`
  14. `idx_audit_org_time` — `ON audit_events(organization_id, created_at DESC)`
  15. `idx_audit_resource` — `ON audit_events(resource_type, resource_id)`
- **Acceptance criteria:**
  - All 16 indexes created (some compound — 15 listed above from database-design.md §3, plus implicit PK indexes)
  - Partial indexes (WHERE clauses) created correctly
  - Descending indexes created correctly
  - Downgrade drops all indexes
- **Verification:**
  ```bash
  alembic upgrade head  # Creates all indexes
  psql -d chronoarb -c "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' ORDER BY indexname;"
  # Count: 15+ compound indexes
  psql -d chronoarb -c "\di idx_*"
  ```
- **Rollback:** `alembic downgrade -1` drops all indexes

---

### DB-10: Upgrade Real Database

- **Size:** XS
- **Files affected:** None (database operation)
- **Dependencies:** DB-09
- **Acceptance criteria:**
  - `alembic upgrade head` runs without errors
  - All 25 tables + all indexes created
  - All ENUM types created
  - `alembic current` shows the head revision
- **Verification:**
  ```bash
  export DATABASE_URL=postgresql+asyncpg://postgres:chronoarb@localhost:5432/chronoarb
  alembic upgrade head
  alembic current
  # → 004_indexes (head)
  ```
- **Rollback:** `alembic downgrade base` drops everything

---

### DB-11: Verify Schema

- **Size:** XS
- **Files affected:** None (verification only)
- **Dependencies:** DB-10
- **Acceptance criteria:**
  - 25 tables confirmed
  - All ENUM types confirmed
  - alert_deliveries has organization_id + material_version (ADR-0002)
  - normalized_listings has observation_at, fx_source, fx_date (ADR-0004, ADR-0005)
  - No composite UNIQUE on alert_deliveries
  - All 15+ indexes confirmed
  - All foreign keys resolve (no orphan references)
- **Verification:**
  ```bash
  psql -d chronoarb -c "\dt" | wc -l  # 25 tables + header
  psql -d chronoarb -c "\d alert_deliveries"                            # Manual inspection
  psql -d chronoarb -c "\d normalized_listings"                         # Manual inspection
  psql -d chronoarb -c "\di" | wc -l                                    # Index count
  psql -d chronoarb -c "SELECT typname FROM pg_type WHERE typtype='e';" # Enum types
  ```

---

### DB-12: Upgrade /ready Endpoint to Real DB Check

- **Size:** XS
- **Files affected:** `apps/api/apps/api/deps.py`, possibly `apps/api/apps/api/routes/ready.py`
- **Dependencies:** DB-04, DB-10
- **Acceptance criteria:**
  - `get_db_status()` executes `SELECT 1` against the real database
  - Returns `"connected"` when database is reachable
  - Returns `"unreachable"` when connection fails
  - `/ready` returns `HTTP 200` with `{"status":"ok","database":"connected"}` when DB is reachable
  - `/ready` returns `HTTP 503` with `{"status":"error","database":"unreachable"}` when DB is unreachable
  - Test `test_ready_returns_200` (renamed: `test_ready_connected`) asserts `200` + `"connected"`
  - New test `test_ready_returns_503_when_db_unreachable` asserts `503` + `"unreachable"`
- **Verification:**
  ```bash
  # With database running
  curl http://localhost:8000/ready | python -m json.tool
  # → {"data":{"status":"ok","database":"connected","trace_id":"trc_..."}}  (HTTP 200)
  
  # With database stopped
  docker stop chronoarb-pg
  curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ready
  # → 503
  curl http://localhost:8000/ready | python -m json.tool
  # → {"data":{"status":"error","database":"unreachable","trace_id":"trc_..."}}
  docker start chronoarb-pg
  ```
- **Files modified:**
  - `apps/api/apps/api/deps.py` — Real `async def get_db_status()` with `SELECT 1`
  - `apps/api/apps/api/routes/ready.py` — Returns `HTTP 503` when DB is unreachable, `HTTP 200` when connected
- **Rollback:** Revert to `return "not_configured"`

---

### DB-13: Write Integration Tests for Database Connectivity

- **Size:** Small
- **Files affected:** `apps/api/tests/conftest.py`, `apps/api/tests/test_database.py`
- **Dependencies:** DB-04, DB-10
- **Acceptance criteria:**
  - `conftest.py` with pytest fixtures:
    - `test_engine` — creates a test database (or uses transaction rollback)
    - `test_session` — yields an async session, rolls back after test
  - `test_database.py` with tests:
    - `test_engine_connects` — engine can acquire a connection
    - `test_session_executes_select` — session can execute `SELECT 1`
    - `test_get_db_yields_session` — get_db dependency yields a usable session
    - `test_get_db_status_connected` — get_db_status returns "connected" when DB is up
  - All tests clean up after themselves (no test data left in database)
- **Verification:**
  ```bash
  pytest apps/api/tests/test_database.py -v
  # → 4 tests passed
  ```
- **Files created:**
  - `apps/api/tests/conftest.py` — Engine and session fixtures
  - `apps/api/tests/test_database.py` — Database integration tests
- **Rollback:** Remove `test_database.py` and `conftest.py` additions

---

### DB-14: Downgrade and Re-Upgrade Migration

- **Size:** XS
- **Files affected:** None (migration execution)
- **Dependencies:** DB-10
- **Acceptance criteria:**
  - `alembic downgrade base` drops all 25 tables, ENUMs, and indexes without errors
  - `alembic upgrade head` re-creates everything without errors
  - Database is in clean state after re-upgrade
  - All 25 tables exist after re-upgrade
- **Verification:**
  ```bash
  alembic downgrade base    # → "No current revision." (empty database)
  alembic upgrade head      # → "Migrating... done"
  psql -d chronoarb -c "\dt" | wc -l  # → 25
  alembic current           # → "004_indexes (head)"
  ```
- **Rollback:** Already verified — this IS the rollback test

---

### DB-15: Update Test Fixtures for Database-Dependent Tests

- **Size:** Small
- **Files affected:** `apps/api/tests/test_health.py`, `apps/api/tests/conftest.py`
- **Dependencies:** DB-04, DB-10, DB-12
- **Acceptance criteria:**
  - `test_ready_connected` asserts `200` + `{"status":"ok","database":"connected"}`
  - `test_ready_503_when_db_unreachable` asserts `503` + `{"status":"error","database":"unreachable"}`
  - Test fixtures use a test database or in-memory SQLite for fast test execution
  - Tests that need a real database use the `test_engine` fixture
  - Tests that don't need a database (health) continue to use the ASGI app directly
- **Verification:**
  ```bash
  pytest apps/api/tests/ -v
  # → All existing tests pass + new database tests pass
  ```
- **Files modified:**
  - `apps/api/tests/test_health.py` — Updated assertions for ready endpoint (200 + 503)
  - `apps/api/tests/conftest.py` — Updated with DB fixtures
- **Rollback:** Revert test assertions to `"not_configured"`

---

## 4. Migration File Strategy

### Why 4 Migration Files Instead of 1

The execution batches plan calls for a single `001_initial_schema.py` (WF-19). This plan splits it into 4 files for the following reasons:

1. **Reviewability:** A single 400+ line migration file is hard to review. Three table migrations (DB-06/07/08) + one index migration (DB-09) enable focused review.

2. **Atomicity at domain boundaries:** If a single migration with 25 tables fails on table 18, the entire migration is rolled back. Splitting enables partial success and easier debugging:
   - `001_identity_and_catalog.py` — Fails if identity/catalog/sources schema is wrong
   - `002_listings_and_valuation.py` — Fails if listing/valuation schema is wrong
   - `003_alerts_and_operations.py` — Fails if alert/operations schema is wrong
   - `004_indexes.py` — Fails if index syntax is wrong (no data to rebuild)

3. **Parallel development:** DB-06, DB-07, and DB-08 have no dependencies on each other. They can be written in parallel by different engineers, then DB-09 adds indexes.

### Migration Naming Convention

```
alembic/versions/
├── 001_identity_and_catalog.py
├── 002_listings_and_valuation.py
├── 003_alerts_and_operations.py
└── 004_indexes.py
```

Alembic revision IDs are auto-generated. The numeric prefix in the filename is a human-readable ordering convention. Alembic uses the dependency tree (`down_revision`), not filename ordering.

### Migration Template

Each migration file follows this structure:

```python
"""Identity and catalog tables — organizations, users, memberships, brands, references, aliases, watch_lists, watch_list_entries.

Revision ID: {auto}
Revises: {previous or None}
Create Date: 2026-08-03 {time}
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "{auto}"
down_revision: Union[str, None] = "{previous or None}"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types first
    op.execute("CREATE TYPE membership_role AS ENUM ('owner', 'admin', 'dealer', 'viewer')")

    # Create tables in dependency order (parents before children)
    op.create_table(
        "organizations",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), unique=True, nullable=False),
        sa.Column("settings", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # ... more tables ...


def downgrade() -> None:
    # Drop tables in reverse creation order
    op.drop_table("watch_list_entries")
    op.drop_table("watch_lists")
    op.drop_table("aliases")
    op.drop_table("references")
    op.drop_table("brands")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("organizations")

    # Drop ENUM types last
    op.execute("DROP TYPE membership_role")
```

---

## 5. ENUM Type Strategy

### Decision: PostgreSQL Native ENUMs

ENUM values are stored as PostgreSQL native ENUM types, not `VARCHAR` with CHECK constraints.

**Rationale:**
- Database-level type safety (invalid values rejected by PostgreSQL, not application code)
- `psql \d table` shows the ENUM values directly
- Adding new ENUM values requires `ALTER TYPE`, which is an explicit migration step (discourages casual changes)
- Matches database-design.md specification (all ENUM fields specify values in the schema)

**ENUM types defined:**

| ENUM Name | Values | Used By |
|-----------|--------|---------|
| `membership_role` | `owner`, `admin`, `dealer`, `viewer` | memberships.role |
| `listing_status` | `active`, `quarantined`, `suppressed`, `stale` | normalized_listings.status |
| `opportunity_state` | `published`, `dismissed`, `contacted`, `purchased`, `expired` | opportunities.state |
| `delivery_status` | `pending`, `sent`, `failed`, `suppressed` | alert_deliveries.delivery_status |
| `feedback_decision` | `purchased`, `contacted`, `dismissed` | feedbacks.decision |
| `subscription_status` | `trialing`, `active`, `past_due`, `canceled`, `unpaid` | subscriptions.status |
| `outbox_event_status` | `pending`, `published`, `failed` | outbox_events.status |

---

## 6. Model and Migration Relationship

### Decision: No SQLAlchemy ORM Models in Batch 3

The initial migration is hand-written SQL via Alembic's `op.create_table()`. SQLAlchemy ORM models are **not created** in Batch 3. This decision is deliberate:

1. **Migrations as source of truth.** The migration defines the schema authoritatively. Creating ORM models before application code needs them creates maintenance overhead (model ↔ migration sync) without benefit.

2. **Models are created when needed.** When repositories and services are implemented (Week 3-5), SQLAlchemy models will be created for the specific tables those repositories access. At that time, models will be validated against the existing migration.

3. **ADR-0005 expand/contract.** When models are created, they only need to reflect the current migration state. Any future schema changes follow the expand/contract pattern: new migration first, then model updates.

**The `Base` and mixins (DB-05) are an exception.** They are infrastructure primitives — not domain models. They provide conventions (timestamping, ULID PKs) that every future model will inherit. Creating them now prevents inconsistency later.

---

## 7. Rollback Considerations

### Per-Migration Rollback

Each migration file has a `downgrade()` function that reverses the `upgrade()` operations. Downgrade order is reverse creation order:

```
tables: created parent → child
downgrade: dropped child → parent
ENUMs: created parent → child
downgrade: dropped child → parent
```

### Full Rollback

```bash
alembic downgrade base
# Drops: 004 indexes → 003 alerts → 002 listings → 001 identity → empty database
```

### Partial Rollback

```bash
alembic downgrade -1  # Rollback one revision
alembic downgrade 002_listings_and_valuation  # Rollback to specific revision
```

### Database Reset

```bash
docker stop chronoarb-pg && docker rm chronoarb-pg
docker run -d --name chronoarb-pg -p 5432:5432 -e POSTGRES_PASSWORD=chronoarb postgres:18
alembic upgrade head
```

---

## 8. Local PostgreSQL Connection

### Database URL

```
postgresql+asyncpg://postgres:chronoarb@localhost:5432/chronoarb
```

Configured via `CHRONOARB_DATABASE_URL` env var (pydantic-settings with `env_prefix="CHRONOARB_"`). Default in `settings.py` is the local Docker connection string.

### Connection Pool

```
pool_size=5           # Minimum connections
max_overflow=15        # Maximum additional connections
pool_timeout=30        # Seconds to wait for connection
pool_recycle=3600      # Recycle connections after 1 hour
pool_pre_ping=True     # Verify connection before use
```

These are sane local development defaults. Production pool size is configured via `CHRONOARB_DB_POOL_SIZE` env var (added to settings.py in Batch 7).

---

## 9. Execution Order

```
DB-01 (PostgreSQL Docker) ──► DB-02 (Create database)
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              DB-03 (Alembic)  DB-04 (Engine)  DB-05 (Mixins)
                    │               │
              ┌─────┼─────┐         │
              │     │     │         │
         DB-06  DB-07  DB-08        │
              │     │     │         │
              └──┬──┴──┬──┘         │
                 │     │            │
              DB-09 (Indexes)       │
                    │               │
              DB-10 (Upgrade) ◄─────┘
                    │
          ┌─────────┼─────────┐
          │         │         │
      DB-11    DB-12    DB-14
      (Verify) (Ready)  (D/G + U/G)
          │         │         │
          └────┬────┴────┬────┘
               │         │
          DB-13 (Tests)  │
               │         │
               └────┬────┘
                    │
              DB-15 (Fixtures)
```

---

## 10. ADR Compliance Checklist

| ADR | Requirement | Migration | Status |
|-----|-------------|-----------|--------|
| ADR-0001 D2 | PostgreSQL sole source of truth | All tables | DB-10 verifies |
| ADR-0001 D3 | NUMERIC for money | valuations, parsed_listings, normalized_listings, trade_outcomes | DB-07 verifies |
| ADR-0001 D4 | TEXT PKs (ULID) | All tables | DB-11 verifies |
| ADR-0001 D7 | organization_id on tenant tables | organizations, memberships, watch_lists, opportunities, alert_rules, alert_deliveries, feedbacks, trade_outcomes, subscriptions, audit_events | DB-11 verifies |
| ADR-0002 D1 | No composite UNIQUE on alert_deliveries | idempotency_key only | DB-08 verifies |
| ADR-0002 D2 | organization_id on alert_deliveries | Column present | DB-11 verifies |
| ADR-0002 D3 | material_version on alert_deliveries | Column present | DB-11 verifies |
| ADR-0004 D1 | observation_at on normalized_listings | Column present, TIMESTAMPTZ NOT NULL | DB-07 verifies |
| ADR-0005 D1 | fx_source + fx_date on normalized_listings | Columns present, TEXT NOT NULL, DATE NOT NULL | DB-07 verifies |
| ADR-0007 | No dependency violations | Not applicable to migrations (no Python imports in migration files) | — |
