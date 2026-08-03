# ChronoArb — Developer Onboarding Guide

**Document type:** New engineer onboarding reference
**Date:** 2026-08-03T22:03:47+05:00
**Status:** Current as of Phase 2 closure
**Authority order:** AGENTS.md > Architecture docs > ADRs > this document

---

## 1. Welcome and Product Overview

### What ChronoArb Is

ChronoArb is a **dealer-acquisition intelligence platform** for professional luxury watch dealers. It ingests watch listings from approved third-party sources, normalizes them to a canonical catalog, computes all-in acquisition costs and expected resale values, and alerts dealers to arbitrage opportunities.

The core question the product answers: **"Should I buy this watch at this price?"** — answered with traceable data, not speculation.

### Target Users

Professional luxury watch dealers who buy from multiple online sources (eBay, Chrono24, dealer networks) and resell through known exit channels. Each dealer operates within an **organization** (tenant) with their own cost assumptions, fee structures, and watch lists.

### Business Problem

Luxury watches have volatile secondary-market pricing. A Rolex Submariner 116610LN may list for $11,500 on one source and $13,200 on another. After accounting for buyer fees, authentication costs, shipping, taxes, and risk reserves, the all-in acquisition cost determines whether the dealer can resell profitably. Dealers currently track this manually across browser tabs and spreadsheets. ChronoArb automates the discovery, normalization, valuation, and alerting pipeline.

### Product Workflow

```
Sources (eBay, Chrono24, dealer networks)
    │
    ▼
Raw Evidence (immutable snapshots of listings)
    │
    ▼
Parsed Listings (structured extraction: price, title, condition, seller)
    │
    ▼
Normalized Listings (matched to canonical watch reference, FX-normalized price)
    │
    ▼
Valuation (all-in acquisition cost, expected resale, profit estimate)
    │
    ▼
Opportunities (tenant-scored, published to dealer feed with material versions)
    │
    ▼
Alerts (rule-based matching → Telegram/FCM push notifications)
    │
    ▼
Dealer Feedback (purchased / contacted / dismissed decisions)
    │
    ▼
Trade Outcomes (realized profit/loss, feeding model calibration)
```

### What Exists Today

- Complete architecture documentation (system design, database design, API contract, security model)
- 12 Architecture Decision Records (ADRs) covering all foundational choices
- Monorepo with Python (FastAPI) backend, TypeScript/Flutter frontends (untouched)
- PostgreSQL 17 database with 25 tables, 7 ENUM types, 12 application indexes
- 4 Alembic migrations establishing the full initial schema
- SQLAlchemy 2.0 async ORM foundation with `BaseRepository`, `TenantRepository`, `UnitOfWork`
- 9 implemented ORM models (identity + catalog slice from Migration 001)
- 8 concrete repository implementations
- 8 Pydantic response schemas
- `/health` and `/ready` operational endpoints with trace ID middleware
- 90 passing tests (57 API + 33 domain)
- Local development environment (Docker PostgreSQL, SQLite fallback, Makefile)

### What Is Still Planned

- Migration 002/003 ORM models (listings, valuation, opportunities, alerts, feedback, billing, operations)
- Authentication middleware (Cognito OIDC)
- Source adapter implementations (3 approved sources)
- Worker pipeline (discovery → fetch → parse → normalize → valuate → match → notify)
- API routes for all modules
- Web dashboard (Next.js) and mobile app (Flutter)
- Stripe billing integration
- The remaining 13 phases of the 16-week roadmap

---

## 2. Current Project Status

### Completed Milestones

| Milestone | Status | Key Outcomes |
|-----------|--------|-------------|
| Architecture foundation | Complete | Project analysis, system/database/API/frontend/worker/security/roadmap docs, ADR-0001 |
| Repository foundation | Complete | Monorepo scaffolding, pnpm workspaces, toolchain configs, import-linter |
| Backend foundation | Complete | FastAPI app shell, health/ready endpoints, trace ID middleware, domain value objects (Money, ULID, errors, SourceAdapter Protocol) |
| Database foundation (Batch 3) | Complete | 25 tables, 7 ENUMs, 12 indexes, 4 migrations, SQLAlchemy engine, session factory |
| Week 2 Phase 1 | **Closed** | BaseRepository, TenantRepository, UnitOfWork, identity ORM models, FK enforcement, session guards |
| Week 2 Phase 2 | **Closed** | Catalog ORM models (6), identity + catalog repositories (8), Pydantic schemas (8), 90 tests |

### Verified Current State

| Metric | Value | Verified |
|--------|-------|----------|
| PostgreSQL tables | 25 | `\dt` |
| ENUM types | 7 | `SELECT * FROM pg_type WHERE typtype='e'` |
| Application indexes | 12 | `\di idx_*` |
| Alembic migrations | 4 | `alembic/versions/*.py` |
| Migration head | `f2b39ba97b17` | `alembic_version` table |
| Revision chain | `a40b5bfef9a2` → `12e1f9e711d2` → `de4e1b0ff4a3` → `f2b39ba97b17` | `alembic history` |
| API tests | 57 | `pytest apps/api/tests/` |
| Domain tests | 33 | `pytest packages/domain-python/tests/` |
| Total tests | 90 | Both suites |

### Phase 3 Status

**Not yet implemented.** Phase 3 covers Migration 002 ORM models (listings, valuation, opportunities) and their repositories. The plan is in `docs/implementation/week-02-domain-plan.md`. No Phase 3 code should be assumed to exist unless found in the repository.

---

## 3. Architecture Overview

ChronoArb follows a **modular monolith with async workers** pattern. The customer-facing API is a single FastAPI application. Long-running ingestion, normalization, valuation, matching, and notification work execute in separate worker processes.

### Layer Architecture

```
┌──────────────────────────────────────┐
│  API Layer                           │
│  Routes, middleware, Pydantic schemas │
│  No business logic, no SQLAlchemy    │
├──────────────────────────────────────┤
│  Application Layer                   │
│  Services, commands, transactions    │
│  Orchestrates repositories + domain  │
├──────────────────────────────────────┤
│  Domain Layer                        │
│  Pure business rules, value objects  │
│  No I/O, no framework dependencies   │
├──────────────────────────────────────┤
│  Infrastructure Layer                │
│  ORM models, repositories, sessions  │
│  External gateways, database access  │
└──────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Location | Contains | Must NOT Import |
|-------|----------|----------|-----------------|
| **API** | `{module}/api/` | HTTP routes, middleware, Pydantic request/response schemas | Repositories, ORM models, SQLAlchemy |
| **Application** | `{module}/application/` | Service classes, transaction orchestration, commands/queries | (Not yet implemented) |
| **Domain** | `{module}/domain/` | Pure business rules, policies, formulas. Persistence-agnostic interfaces only. | SQLAlchemy, ORM models, repositories |
| **Infrastructure** | `{module}/infrastructure/` | SQLAlchemy models, repositories, database sessions, Unit of Work | Domain logic (must not contain business rules) |

### Critical Rule: Repositories in Infrastructure

Concrete repositories that import SQLAlchemy, inherit `BaseRepository`/`TenantRepository`, depend on ORM models, or execute persistence queries MUST live under `infrastructure/`. They must NEVER live under `domain/`. This was verified and corrected in Week 2 Phase 2 (CR-10).

The `domain/` directory may contain Protocol/ABC interfaces for repositories ONLY when they are persistence-agnostic — no SQLAlchemy imports, no ORM model dependencies.

### Dependency Diagram

```mermaid
graph TD
    API[API Layer] --> APP[Application Layer]
    APP --> DOMAIN[Domain Layer]
    APP --> INFRA[Infrastructure Layer]
    INFRA --> DOMAIN
    DOMAIN --> PKG[packages/domain-python]
    INFRA --> PKG
```

---

## 4. Repository and Monorepo Structure

### Important Directories

| Path | Purpose | Status |
|------|---------|--------|
| `apps/api/` | FastAPI modular monolith | Core app operational, 12 modules created, 2 implemented |
| `apps/worker/` | Worker process entry points | Skeleton only — no pipeline code yet |
| `apps/web/` | Next.js dashboard | Not started |
| `apps/mobile/` | Flutter app | Not started |
| `packages/domain-python/` | Shared domain value objects | Money, ULID, errors, SourceAdapter Protocol |
| `packages/source-adapters/` | Source-specific fetch/parse | Placeholder only — Protocol defined, no implementations |
| `packages/api-client-ts/` | Generated TypeScript client | Placeholder |
| `packages/api-client-dart/` | Generated Dart client | Placeholder |
| `packages/design-tokens/` | Shared visual tokens | Placeholder |
| `docs/architecture/` | System, database, API, frontend, worker, security designs | Complete |
| `docs/adr/` | Architecture Decision Records | 9 ADRs (0001-0009) |
| `docs/implementation/` | Sprint and task plans | Week 1-2 plans, migration plans |
| `docs/reviews/` | Implementation reviews and closures | Batch 1-3, Week 2 Phase 1-2 |
| `alembic/` | Database migrations | 4 files (001-004), hand-written |
| `infrastructure/terraform/` | AWS infrastructure as code | Plan-only, not applied |

### Key Configuration Files

| File | Purpose |
|------|---------|
| `package.json` | Root workspace, `pnpm` scripts, `turbo` dev dependency |
| `pnpm-workspace.yaml` | Workspace members: `apps/*`, `packages/*` |
| `turbo.json` | Pipeline stages: build, lint, typecheck, test |
| `pyproject.toml` | Python tooling: ruff (py313), mypy (strict), pytest |
| `.importlinter` | 4 contracts enforcing Python dependency boundaries |
| `Makefile` | Database migration, reset, and status commands |
| `alembic.ini` | Alembic configuration (reads `CHRONOARB_DATABASE_URL`) |
| `.gitignore` | Excludes node_modules, `__pycache__`, `.env`, `.terraform`, dist |

### Command Reference

| Command | Purpose |
|---------|---------|
| `pnpm install` | Install workspace dependencies |
| `pnpm turbo run build` | Build all packages |
| `make db-reset` | Full database reset (drop schema, re-apply all migrations) |
| `make db-status` | Show current migration state, tables, ENUMs |
| `make db-clean` | Drop all database objects (destructive) |
| `source .venv/bin/activate` | Activate Python virtual environment |
| `cd apps/api && python -m pytest tests/ -v` | Run API test suite |
| `cd packages/domain-python && python -m pytest tests/ -v` | Run domain test suite |

---

## 5. Module Structure

Every backend module follows a standard 4-subdirectory structure, created in Batch 2:

```
{module}/
├── api/              # HTTP routes, Pydantic schemas (Week 3-5)
├── application/      # Service classes, commands (Week 2 Day 5+)
├── domain/           # Pure business rules (empty for most modules currently)
└── infrastructure/   # ORM models, repositories, persistence
```

### Example: Identity Module

```
identity/
├── api/
│   └── schemas.py                       # OrganizationResponse, UserResponse, MembershipResponse
├── application/
│   └── __init__.py                      # Empty — services planned for Week 2 Day 5
├── domain/
│   └── __init__.py                      # Empty — pure business rules
└── infrastructure/
    ├── models.py                        # Organization, User, Membership
    └── repositories.py                  # OrganizationRepository, UserRepository, MembershipRepository
```

### Example: Catalog Module

```
catalog/
├── api/
│   └── schemas.py                       # BrandResponse, SourceResponse, ReferenceResponse, WatchListResponse, WatchListEntryResponse
├── application/
│   └── __init__.py                      # Empty
├── domain/
│   └── __init__.py                      # Empty
└── infrastructure/
    ├── models.py                        # Brand, Source, WatchList, Reference, Alias, WatchListEntry
    └── repositories.py                  # BrandRepository, SourceRepository, ReferenceRepository, WatchListRepository, AliasRepository
```

### Modules Not Yet Implemented

The following modules have directory scaffolding but no implementation code:

`alerts`, `billing`, `duplicates`, `feedback`, `listings`, `normalization`, `operations`, `sources`, `valuation`, `opportunities`

---

## 6. Current Implemented Models

### Identity Models (Phase 1)

| Model | Table | Scope | Notable |
|-------|-------|-------|---------|
| `Organization` | `organizations` | Global | Has JSONB `settings` field using dialect-aware `JSON().with_variant(JSONB(), "postgresql")` |
| `User` | `users` | Global | Has `foreign_keys="Membership.user_id"` to resolve FK ambiguity with `invited_by` |
| `Membership` | `memberships` | Tenant-scoped | FK to orgs + users + users(inviter). `role` is `Text()` in ORM — PostgreSQL ENUM enforces valid values. No `updated_at` (immutable after creation). |

### Catalog Models (Phase 2)

| Model | Table | Scope | Notable |
|-------|-------|-------|---------|
| `Brand` | `brands` | Global | `name` and `slug` are UNIQUE. Only `created_at` — no `updated_at`. |
| `Source` | `sources` | Global (platform) | `rate_policy` is JSONB variant. `is_enabled` defaults to `false`. |
| `WatchList` | `watch_lists` | Tenant-scoped | FK to organizations. Only `created_at`. |
| `Reference` | **`"references"`** | Global | **Table name requires double-quoting** — it's a PostgreSQL reserved word. `attributes` is JSONB variant. `is_active` defaults to `true` with `server_default=sa.text("true")`. UNIQUE on `(brand_id, ref_code)`. |
| `Alias` | `aliases` | Global | Maps alias text to a canonical reference. **No timestamp columns at all** (matches migration 001). UNIQUE on `(alias_text, source)`. |
| `WatchListEntry` | `watch_list_entries` | Indirect tenant | FK to watch_lists + references. UNIQUE on `(watch_list_id, reference_id)`. Tenant scope inherited through WatchList's `organization_id`. |

---

## 7. Repository Layer

### Base Classes

Located in `apps/api/apps/api/infrastructure/repository.py`:

| Class | Purpose | Key Behavior |
|-------|---------|-------------|
| `BaseRepository[Model]` | Generic CRUD for global entities | `save()`, `delete()`, `get_by_id()`, `list_all()`, `count()`. Uses `flush()` not `commit()` — caller owns transaction. |
| `TenantRepository[Model]` | Generic CRUD for tenant-scoped entities | Extends `BaseRepository`. `get_by_id()` checks model's `organization_id` matches supplied parameter. Cross-tenant returns `None`. `list_by_org()` uses `WHERE organization_id = $1`. |

### Current Safeguards

| Guard | Behavior |
|-------|----------|
| Session guard | `BaseRepository(session=None)` raises `TypeError("requires a session")` |
| Tenant model guard | `TenantRepository(..., model_cls=Model)` validates `organization_id` column exists |
| Cross-tenant isolation | Queries with wrong org_id return `None` or empty list |
| No implicit commit | Repositories flush but never commit — transaction boundary is the caller's responsibility |
| No unrestricted list | `list_by_org()` always requires `organization_id` |

### Concrete Repositories (8)

**Identity** (`identity/infrastructure/repositories.py`):

| Repository | Base Class | Methods |
|-----------|------------|---------|
| `OrganizationRepository` | `BaseRepository` | `get_by_slug(slug)` |
| `UserRepository` | `BaseRepository` | `get_by_cognito_sub(sub)`, `get_by_email(email)` |
| `MembershipRepository` | `TenantRepository` | `get_by_user_and_org(user_id, org_id)`, `list_members(org_id)` |

**Catalog** (`catalog/infrastructure/repositories.py`):

| Repository | Base Class | Methods |
|-----------|------------|---------|
| `BrandRepository` | `BaseRepository` | `get_by_name(name)`, `get_by_slug(slug)` |
| `SourceRepository` | `BaseRepository` | Standard CRUD only |
| `ReferenceRepository` | `BaseRepository` | `get_by_brand_and_ref_code(brand_id, ref_code)` |
| `WatchListRepository` | `TenantRepository` | Standard CRUD + `list_by_org()` |
| `AliasRepository` | `BaseRepository` | `find_by_alias_text(alias_text)` → `list[Alias]` |

### Unit of Work

Located at `apps/api/apps/api/infrastructure/uow.py`:

```python
async with UnitOfWork() as uow:
    repo = uow.repository(OrganizationRepository)
    await repo.save(org)
    await uow.commit()  # Explicit — must be called
# If commit() is not called, changes are silently rolled back at session close
```

- `commit()` and `rollback()` raise `RuntimeError` if called outside `async with` context
- `__aexit__` closes the session if the UoW created it
- Repository factory uses the same active session
- No double-commit guard (second call is a no-op)

---

## 8. Tenant Isolation Rules

Tenant isolation is the most critical security boundary in ChronoArb. Dealer strategies and financial outcomes are commercially sensitive. Incorrect tenant scoping is a data breach.

### Rules

1. Every query against a tenant-owned table MUST include `organization_id` in the WHERE clause.
2. The `organization_id` parameter on repository methods is mandatory — no default, no optional argument.
3. Cross-tenant access returns `None` (not 403). Attackers cannot distinguish "doesn't exist" from "not yours."
4. Global tables (brands, references, sources, users, organizations themselves) are accessed through `BaseRepository` — no `organization_id` parameter.
5. Unrestricted list methods on tenant tables are prohibited. List methods must always scope to an organization.
6. Tenant ownership must not be inferred through unrelated joins. The owning model's `organization_id` column is the sole authority.
7. **All tenant isolation repository tests are mandatory** — they must pass before merge.

### Pseudocode Examples

**Safe — tenant query always scoped:**
```python
# Repository method signature requires organization_id
async def list_opportunities(self, organization_id: str) -> list[Opportunity]:
    query = select(Opportunity).where(Opportunity.organization_id == organization_id)
    return (await self.session.execute(query)).scalars().all()
```

**Unsafe — missing tenant scope:**
```python
# NEVER do this — returns opportunities across all organizations
async def list_all_opportunities(self) -> list[Opportunity]:
    query = select(Opportunity)
    return (await self.session.execute(query)).scalars().all()
```

---

## 9. Database and Migration Overview

### PostgreSQL 17

PostgreSQL 17 is the single system of record (ADR-0001 D2). Redis/Valkey is never the sole source of truth. Local development uses Docker PostgreSQL (`postgres:17` image, container `chronoarb-pg`, port 5432).

### Alembic Migrations

All 4 migrations are **hand-written** — no `--autogenerate` is used (ADR-0008). Write DDL via `op.create_table()`, `op.create_index()`, `op.execute()`.

| # | Revision | File | Tables | ENUMs | Indexes |
|---|----------|------|--------|-------|---------|
| 001 | `a40b5bfef9a2` | `001_identity_and_catalog.py` | 9 | 1 | — |
| 002 | `12e1f9e711d2` | `002_listings_and_valuation.py` | 8 | 2 | — |
| 003 | `de4e1b0ff4a3` | `003_alerts_and_operations.py` | 8 | 4 | — |
| 004 | `f2b39ba97b17` | `004_indexes.py` | — | — | 12 |

**Migration head:** `f2b39ba97b17`

### Database Rules

- `NUMERIC(precision, scale)` for all money columns — `float` and `double` are prohibited
- `TEXT` for ULID primary keys — no auto-increment, no UUID
- `TIMESTAMPTZ` for all timestamps with `server_default=func.now()`
- Immutable records (valuations, raw_snapshots, opportunities) have no `updated_at` column
- New material versions create new rows — old versions are preserved
- ENUMs are PostgreSQL native types created with `CREATE TYPE` in the same migration as their first consumer table
- Partial indexes use `postgresql_where=` in Alembic

### Migration Commands

```bash
make db-reset      # Full reset: DROP SCHEMA CASCADE → re-apply all 4 migrations
make db-status     # Show current revision, tables, ENUMs
make db-clean      # Drop everything (destructive)
```

### Known Issue: Per-Migration Downgrade

`make db-migrate` and `make db-rollback` have a known issue with `export` environment variable propagation. Use the direct shell pipeline for individual migration operations:

```bash
CHRONOARB_DATABASE_URL=postgresql+asyncpg://postgres:chronoarb@localhost:5432/chronoarb \
  alembic upgrade head --sql 2>/dev/null \
  | docker exec -i chronoarb-pg psql -U postgres -d chronoarb -q
```

This is caused by Python 3.14 + asyncpg incompatibility (ADR-0009). The fix is deferred to Batch 8 (CI setup).

---

## 10. Local Development Setup

### Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.14.6 | `python3 --version` |
| pnpm | 11.3.0 | `pnpm --version` |
| Docker | 29.x+ | `docker --version` |

### Setup Steps

```bash
# 1. Clone and enter repo
git clone <repo-url> chronoarb
cd chronoarb

# 2. Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Python dependencies
pip install -e packages/domain-python
pip install -e packages/source-adapters
pip install -e 'apps/api[dev]'
pip install -e 'apps/worker[dev]'

# 4. Install Node dependencies
pnpm install

# 5. Start PostgreSQL
docker run -d --name chronoarb-pg -p 5432:5432 \
  -e POSTGRES_PASSWORD=chronoarb \
  -e POSTGRES_DB=chronoarb \
  postgres:17

# 6. Apply migrations
make db-reset

# 7. Verify migration head
make db-status
# Expected: revision f2b39ba97b17, 25 tables, 7 ENUMs

# 8. Run all tests
cd apps/api && python -m pytest tests/ -v
cd ../../packages/domain-python && python -m pytest tests/ -v
# Expected: 57 API + 33 domain = 90 passed

# 9. Start API
cd apps/api && uvicorn apps.api.main:app --reload --port 8000

# 10. Verify health
curl http://localhost:8000/health
# {"data":{"status":"ok","trace_id":"trc_..."}}
```

### Python 3.14 + asyncpg Workaround

The local API uses SQLite (`aiosqlite`) as the database driver because `asyncpg 0.31.0` has unresolved SSL negotiation issues on Python 3.14.6. Production and CI use Python 3.13 + PostgreSQL. See ADR-0009 for full details. The SQLite default is configured in `apps/api/apps/api/settings.py`:

```python
database_url: str = "sqlite+aiosqlite:///chronoarb.db"
```

Override for PostgreSQL testing:
```bash
CHRONOARB_DATABASE_URL=postgresql+asyncpg://postgres:chronoarb@localhost:5432/chronoarb \
  uvicorn apps.api.main:app --port 8000
```

This will timeout after 5 seconds and `/ready` will return `"unreachable"` — expected behavior.

---

## 11. Testing Strategy

### Test Split

| Suite | Location | Count | Framework |
|-------|----------|-------|-----------|
| API tests | `apps/api/tests/` | 57 | pytest + pytest-asyncio |
| Domain tests | `packages/domain-python/tests/` | 33 | pytest |
| **Total** | | **90** | |

### Local Test Behavior

Tests run against **SQLite** (`sqlite+aiosqlite://` in-memory). SQLite cannot validate:

- PostgreSQL ENUM type enforcement (`role` column accepts any string)
- PostgreSQL JSONB operators (`settings->>'key'`)
- PostgreSQL-specific `server_default` values (`sa.text("true")`)
- `NUMERIC(precision, scale)` exact precision enforcement
- `RETURNING` clause for server-generated defaults

### What SQLite CAN Validate

- Foreign key constraints (enabled via `PRAGMA foreign_keys=ON` in test fixtures)
- UNIQUE constraint violations
- NOT NULL constraint violations
- Application-level logic (queries, tenant isolation, pagination)
- Dict round-trips for JSON fields
- Cursor pagination correctness

### CI PostgreSQL Validation

The CI pipeline runs tests against PostgreSQL (Python 3.13 leg). This catches all SQLite-ungated issues: ENUM violations, JSONB operator errors, NUMERIC precision, and DDL correctness. A PR must pass both the SQLite (Python 3.14) and PostgreSQL (Python 3.13) CI legs.

---

## 12. Coding Standards and Non-Negotiable Rules

These rules are extracted from `AGENTS.md`. The complete AGENTS.md is the authoritative source — this section is a summary.

### Python / FastAPI

- Strict type checking (`mypy --strict`)
- SQLAlchemy 2.0 `Mapped[type]` annotations
- Pydantic v2 schemas
- `Decimal` for all money — `float` prohibited
- ULID TEXT primary keys from `packages/domain-python/chronoarb/domain/ulid.py`
- Repository methods that access tenant data MUST require `organization_id`
- Routes handle HTTP only: validation, auth, service call, response mapping

### Database

- Migrations are hand-written — no `--autogenerate`
- ORM models MUST match migration DDL (verify with `Base.metadata.create_all()` comparison)
- No `updated_at` on immutable tables
- Numeric for money, TIMESTAMPTZ for timestamps, TEXT for ULIDs

### Architecture

- Domain layer MUST NOT import SQLAlchemy, ORM models, or repositories
- Concrete repositories MUST live in `infrastructure/`
- No cross-module model imports between ORM files
- No unrelated refactoring — bounded tasks only

### Security

- No secrets in source code, config files, or logs
- Deny by default — explicit tenant scope on every protected query
- Cross-tenant access returns None (not 403)
- No localStorage for access tokens
- No source access bypass, CAPTCHA circumvention, or unauthorized URL fetching

### Process

- Work in bounded phases with review → correction → closure cycles
- Read AGENTS.md before any code change
- Report: implemented, changed, verified, risks
- AGENTS.md overrides this document if they conflict

---

## 13. Known Risks and Accepted Notes

### Accepted Current Notes

| Item | Severity | Description |
|------|----------|-------------|
| `"references"` reserved identifier | NOTE | Table name requires double-quoting in raw SQL. ORM/SQLAlchemy handle this transparently. |
| Membership.role `Text()` mapping | NOTE | PostgreSQL ENUM enforces valid values at DB layer. ORM uses `Text()` — valid values enforced at INSERT time. |
| SQLite ≠ PostgreSQL | NOTE | Tests use SQLite. CI validates PostgreSQL. Never treat SQLite success as proof of PostgreSQL correctness. |
| `server_default=sa.text("true")` | NOTE | PostgreSQL-specific syntax. Python `default=True` ensures correct SQLite behavior. |
| Stripe IDs nullable | NOTE | `subscriptions.stripe_customer_id` and `stripe_subscription_id` are nullable — supports pre-Stripe-integration development. |
| `updated_at` application-layer | NOTE | The `TimestampMixin.updated_at` uses Python `onupdate` lambda but no `server_default` with `ON UPDATE`. Application code must set `updated_at` explicitly on updates. |
| `Alias` has no timestamps | NOTE | Migration 001 creates aliases without `created_at`. This is by design — aliases are catalog metadata. |

### Deferred Technical Debt

| Item | When |
|------|------|
| `asyncpg` Python 3.14 compatibility | Track upstream releases; switch when resolved |
| `subscriptions` indexes on Stripe IDs | Post-MVP when subscription count warrants |
| Python-level ENUM guard for `role` | Phase 3 or later |
| Makefile per-migration downgrade | Batch 8 (CI setup) |
| `import-linter` TOML format conversion | Batch 8 (CI setup) |

### Do NOT "Fix" Without an Approved Task

- Do not change `Alias` to add timestamps — it matches Migration 001
- Do not add a composite UNIQUE to `alert_deliveries` — ADR-0002 deliberately removed it
- Do not change `role` from `Text()` to ENUM in the ORM without understanding the migration implications
- Do not add speculative indexes — Migration 004 defines the complete set
- Do not add `updated_at` to `Brand`, `Source`, `WatchList`, or `Reference` — they don't have it in the migration

---

## 14. Development Workflow

All work follows a bounded, phased workflow:

```
Plan → Review → Corrections → Implementation → Verification → Closure
```

### Step Detail

1. **Plan:** Read AGENTS.md, relevant ADRs, architecture docs, and prior reviews. Create a phased plan with exact file paths, acceptance criteria, and verification commands.
2. **Review:** A separate review pass audits the plan for architecture compliance, scope creep, and correctness.
3. **Corrections:** Apply review findings to the plan before any code is written.
4. **Implementation:** Write code in bounded phases. Do not implement beyond the current phase scope.
5. **Verification:** Run the relevant test suite, verify acceptance criteria, provide evidence.
6. **Closure:** A closure review confirms all acceptance criteria are met, all corrections are applied, and the phase gate is clear.

### Handoff Format

After each implementation phase, report:

```
Implemented
- <requirement/task outcome>

Changed
- <path>: <reason>

Verified
- <command>: <result>

Operational impact
- <migration/flag/config/monitoring/none>

Risks or follow-ups
- <explicit item or none>
```

---

## 15. Phase 3 Starting Point

**⚠️ Next planned work — not yet implemented.**

Phase 3 covers the Migration 002 ORM models (listings and valuation slice) per `docs/implementation/week-02-domain-plan.md`.

### Expected Models (8)

| Model | Table | Migration |
|-------|-------|-----------|
| `RawSnapshot` | `raw_snapshots` | 002 |
| `ParsedListing` | `parsed_listings` | 002 |
| `NormalizedListing` | `normalized_listings` | 002 |
| `DuplicateGroup` | `duplicate_groups` | 002 |
| `DuplicateGroupMember` | `duplicate_group_members` | 002 |
| `Valuation` | `valuations` | 002 |
| `Opportunity` | `opportunities` | 002 |
| `OpportunityView` | `opportunity_views` | 002 |

### Expected Repositories (5)

| Repository | Base Class |
|-----------|------------|
| `ListingRepository` | `BaseRepository` |
| `DuplicateRepository` | `BaseRepository` |
| `ValuationRepository` | `BaseRepository` |
| `OpportunityRepository` | `TenantRepository` |
| (opportunity views through opportunity) | — |

### Key Differences from Migration 001 Models

- `NormalizedListing` has 3 ADR-correction columns: `observation_at` (TIMESTAMPTZ NOT NULL, ADR-0004), `fx_source` (TEXT NOT NULL, ADR-0005), `fx_date` (DATE NOT NULL, ADR-0005)
- `Valuation` has 8 NUMERIC money columns — all must use `Decimal`
- `Opportunity` is tenant-scoped and uses `material_version` for immutable versioning
- `valuations`, `raw_snapshots`, and `opportunities` are immutable — no `updated_at`
- `NormalizedListing` uses `listing_status` ENUM

### Files to Read Before Starting

1. `docs/implementation/week-02-domain-plan.md` — complete Phase 3 scope
2. `alembic/versions/12e1f9e711d2_002_listings_and_valuation.py` — Migration 002 DDL
3. `docs/architecture/database-design.md` §2.3-2.7 — table specifications
4. `docs/adr/0004-customer-visible-data-freshness-model.md` — observation_at requirement
5. `docs/adr/0005-fx-rate-management.md` — FX rate provenance
6. `apps/api/apps/api/infrastructure/models.py` — Base, TimestampMixin, ULIDMixin, TenantMixin
7. `apps/api/apps/api/infrastructure/repository.py` — BaseRepository, TenantRepository
8. `apps/api/apps/api/identity/infrastructure/models.py` — example model patterns
9. `apps/api/apps/api/catalog/infrastructure/models.py` — example model patterns including JSONB variants

---

## 16. First-Day Checklist

- [ ] Obtain repository access and clone
- [ ] Install Python 3.14, pnpm 11.x, Docker
- [ ] Read `AGENTS.md` (top priority — overrides everything)
- [ ] Read `docs/architecture/system-design.md`
- [ ] Read `docs/architecture/database-design.md` §1-3
- [ ] Read `docs/adr/0001-initial-architecture.md`
- [ ] Read `docs/reviews/batch-03-database-completion.md`
- [ ] Set up local environment (see §10 above)
- [ ] Start PostgreSQL Docker container
- [ ] Run `make db-reset`
- [ ] Verify migration head: `f2b39ba97b17`
- [ ] Run all tests: 90/90 passing
- [ ] Inspect `apps/api/apps/api/identity/` and `apps/api/apps/api/catalog/` directories
- [ ] Verify no uncommitted changes: `git status`
- [ ] Ask for your assigned bounded task before writing any code

---

## 17. Common Mistakes to Avoid

| Mistake | Why It's Wrong | Correct Approach |
|---------|---------------|-----------------|
| Placing concrete repositories in `domain/` | Violates layer dependency rules | Always put in `infrastructure/` |
| Creating a migration to fix an ORM-only mismatch | Migration is schema source of truth | Fix the ORM model to match the migration |
| Using `float` for money | Violates AGENTS.md §2 | Use `Decimal` with `NUMERIC(precision, scale)` |
| Omitting `organization_id` on tenant queries | Data breach — exposes other orgs' data | Mandatory parameter on all tenant repository methods |
| Trusting SQLite tests as PostgreSQL proof | SQLite doesn't enforce ENUMs, JSONB operators, or NUMERIC precision | CI PostgreSQL leg is the gate |
| Exposing ORM models directly through API routes | Violates AGENTS.md §9 | Map to Pydantic response schemas via `model_validate()` |
| Committing inside a repository method | Breaks transaction boundaries | Repositories `flush()` only — caller calls `commit()` |
| Modifying immutable evidence | Violates ADR-0001 D10 | Create new material versions — never UPDATE |
| Adding speculative methods or indexes | Creates maintenance debt | Only implement what the plan specifies |
| Starting Phase 3 before Phase 2 closure | Phases build on verified foundations | Wait for the closure verdict |
| Bypassing source access restrictions | Legal and contractual violation | Sources must be approved, documented, and isolated in adapters |

---

## 18. Glossary

| Term | Meaning in ChronoArb |
|------|---------------------|
| **Organization / Tenant** | A dealer's company. All tenant data is scoped by `organization_id`. Different orgs have different cost assumptions and see different opportunities from the same listings. |
| **Reference** | A canonical watch model (e.g., Rolex Submariner Date 116610LN). Each reference belongs to a brand. The `references` table uses `"references"` quoting. |
| **Alias** | An alternative name for a reference (e.g., "Sub Date", "116610"). Used by the normalization engine to match source listings to canonical references. |
| **Raw Snapshot** | Immutable copy of a listing as it appeared at a source at a point in time. Stored before parsing. |
| **Parsed Listing** | Structured extraction from a raw snapshot (price, title, condition, seller info). |
| **Normalized Listing** | A parsed listing matched to a canonical reference with currency-normalized price, FX rate provenance, and observation timestamp. |
| **Valuation** | Computed financial analysis: all-in acquisition cost, expected resale value, expected profit, ROI. Uses comparable-based estimation with condition/set/geography adjustments. |
| **Opportunity** | A listing surfaced to a specific organization as potentially profitable. Tenant-scoped. New valuation → new material version → new opportunity row. |
| **Material Version** | An integer that increments each time an opportunity's underlying data changes (new valuation, price change). Old versions are preserved (immutable). |
| **Idempotency Key** | A SHA256 hash (org + user + rule + opportunity + version + channel) that prevents duplicate alert deliveries. UNIQUE constraint enforces it. |
| **Outbox Event** | A record in the `outbox_events` table written in the same transaction as a state change. The outbox worker publishes it to SQS for async processing. |
| **Unit of Work (UoW)** | An async context manager that wraps a database session, manages commit/rollback, and provides repository factories. |
| **Source Adapter** | A source-specific module implementing the `SourceAdapter` Protocol. Handles discovery, fetch, and parse for one source. Never imported by core modules. |

---

## 19. Quick Reference

### Key Documents

| Document | Path |
|----------|------|
| Engineering rules | `AGENTS.md` |
| System design | `docs/architecture/system-design.md` |
| Database design | `docs/architecture/database-design.md` |
| API contract | `docs/architecture/api-design.md` |
| Security model | `docs/architecture/security-model.md` |
| Initial architecture (ADR-0001) | `docs/adr/0001-initial-architecture.md` |
| Week 2 plan | `docs/implementation/week-02-domain-plan.md` |
| DB completion | `docs/reviews/batch-03-database-completion.md` |
| Phase 1 closure | `docs/reviews/week-02-phase-01-closure.md` |
| Phase 2 review | `docs/reviews/week-02-phase-02-review.md` |

### Important Commands

| Command | Purpose |
|---------|---------|
| `source .venv/bin/activate` | Activate Python venv |
| `pip install -e 'apps/api[dev]'` | Install API + dev deps |
| `make db-reset` | Full DB reset + re-apply all migrations |
| `make db-status` | Show migration state |
| `cd apps/api && python -m pytest tests/ -v` | Run API tests (57) |
| `cd packages/domain-python && python -m pytest tests/ -v` | Run domain tests (33) |
| `uvicorn apps.api.main:app --reload --port 8000` | Start API |
| `curl http://localhost:8000/health` | Health check |

### Module Dependency Direction

```
Domain Layer (packages/domain-python)
    ↑
Infrastructure Layer (ORM models, repositories)
    ↑
Application Layer (services — not yet implemented)
    ↑
API Layer (routes — not yet implemented)
```

### Current State Summary

| Metric | Value |
|--------|-------|
| Migration head | `f2b39ba97b17` |
| Tables | 25 |
| ENUMs | 7 |
| Application indexes | 12 |
| ORM models implemented | 9 |
| Repositories implemented | 8 |
| Tests passing | 90 (57 API + 33 domain) |
| Current phase | Phase 2 — CLOSED |
| Next phase | Phase 3 — NOT STARTED |
| System of record | PostgreSQL 17 (Docker) |
| Local dev DB | SQLite (aiosqlite fallback) |
