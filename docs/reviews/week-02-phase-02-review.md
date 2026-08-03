# Week 02 Phase 02 — Implementation Review

**Review type:** Post-implementation architecture audit
**Reviewed files:** 8 production files, 1 test file
**Date:** 2026-08-03T19:14:33+05:00
**Reviewer:** Architecture review pass
**Cross-referenced:** Migration 001 DDL, week-02-domain-plan.md, phase-01-closure.md

---

## Executive Summary

Phase 2 delivers 6 catalog ORM models, 8 repositories, and 8 Pydantic response schemas across 9 files. The ORM models match Migration 001 exactly on every column, type, constraint, and default. JSONB variants compile correctly. The `"references"` reserved-word table is properly quoted. 90 tests pass with FK enforcement active. However, the repository files are placed in `domain/` — a layer violation that puts concrete infrastructure code in the domain namespace. This must be corrected before Phase 3.

**Verdict: APPROVED WITH CORRECTIONS**

---

## 1. Migration 001 ORM Parity

### organizations

| Column | Migration | ORM Model | Match? |
|--------|-----------|-----------|--------|
| id | TEXT PK | `ULIDMixin.id` | YES |
| name | TEXT NOT NULL | `Text(), nullable=False` | YES |
| slug | TEXT UNIQUE NOT NULL | `Text(), unique=True, nullable=False` | YES |
| settings | JSONB nullable | `JSON().with_variant(JSONB(), "postgresql"), nullable=True` | YES |
| created_at | TIMESTAMPTZ DEFAULT NOW() | `TimestampMixin.created_at` | YES |
| updated_at | TIMESTAMPTZ DEFAULT NOW() | `TimestampMixin.updated_at` | YES |

### users

| Column | Migration | ORM Model | Match? |
|--------|-----------|-----------|--------|
| id | TEXT PK | `ULIDMixin.id` | YES |
| cognito_sub | TEXT UNIQUE NOT NULL | `Text(), unique=True, nullable=False` | YES |
| email | TEXT UNIQUE NOT NULL | `Text(), unique=True, nullable=False` | YES |
| display_name | TEXT nullable | `Text(), nullable=True` | YES |
| created_at | TIMESTAMPTZ DEFAULT NOW() | `TimestampMixin.created_at` | YES |
| updated_at | TIMESTAMPTZ DEFAULT NOW() | `TimestampMixin.updated_at` | YES |

### memberships

| Column | Migration | ORM Model | Match? |
|--------|-----------|-----------|--------|
| id | TEXT PK | `ULIDMixin.id` | YES |
| organization_id | FK NOT NULL | `ForeignKey("organizations.id"), nullable=False` | YES |
| user_id | FK NOT NULL | `ForeignKey("users.id"), nullable=False` | YES |
| role | membership_role ENUM NOT NULL | `Text(), nullable=False` | NOTE (CR-02) |
| invited_by | FK nullable | `ForeignKey("users.id"), nullable=True` | YES |
| created_at | TIMESTAMPTZ DEFAULT NOW() | `TIMESTAMP, server_default=func.now()` | YES |
| UNIQUE | (user_id, organization_id) | UniqueConstraint in __table_args__ | YES |

### brands

| Column | Migration | ORM Model | Match? |
|--------|-----------|-----------|--------|
| id | TEXT PK | `ULIDMixin.id` | YES |
| name | TEXT UNIQUE NOT NULL | `Text(), unique=True, nullable=False` | YES |
| slug | TEXT UNIQUE NOT NULL | `Text(), unique=True, nullable=False` | YES |
| created_at | TIMESTAMPTZ DEFAULT NOW() | `TIMESTAMP, server_default=func.now()` | YES |

### sources

| Column | Migration | ORM Model | Match? |
|--------|-----------|-----------|--------|
| id | TEXT PK | `ULIDMixin.id` | YES |
| source_key | TEXT UNIQUE NOT NULL | `Text(), unique=True, nullable=False` | YES |
| display_name | TEXT NOT NULL | `Text(), nullable=False` | YES |
| adapter_version | TEXT NOT NULL | `Text(), nullable=False` | YES |
| access_mode | TEXT NOT NULL | `Text(), nullable=False` | YES |
| rate_policy | JSONB nullable | `JSON().with_variant(JSONB(), "postgresql"), nullable=True` | YES |
| approval_ref | TEXT nullable | `Text(), nullable=True` | YES |
| is_enabled | BOOLEAN DEFAULT false | `Boolean(), default=False, server_default=sa.text("false")` | YES |
| created_at | TIMESTAMPTZ DEFAULT NOW() | `TIMESTAMP, server_default=func.now()` | YES |

### watch_lists

| Column | Migration | ORM Model | Match? |
|--------|-----------|-----------|--------|
| id | TEXT PK | `ULIDMixin.id` | YES |
| organization_id | FK NOT NULL | `ForeignKey("organizations.id"), nullable=False` | YES |
| name | TEXT NOT NULL | `Text(), nullable=False` | YES |
| created_at | TIMESTAMPTZ DEFAULT NOW() | `TIMESTAMP, server_default=func.now()` | YES |

### `"references"`

| Column | Migration | ORM Model | Match? |
|--------|-----------|-----------|--------|
| id | TEXT PK | `ULIDMixin.id` | YES |
| brand_id | FK NOT NULL | `ForeignKey("brands.id"), nullable=False` | YES |
| ref_code | TEXT NOT NULL | `Text(), nullable=False` | YES |
| model_name | TEXT nullable | `Text(), nullable=True` | YES |
| generation | TEXT nullable | `Text(), nullable=True` | YES |
| attributes | JSONB nullable | `JSON().with_variant(JSONB(), "postgresql"), nullable=True` | YES |
| is_active | BOOLEAN DEFAULT true | `Boolean(), default=True, server_default=sa.text("true")` | YES |
| created_at | TIMESTAMPTZ DEFAULT NOW() | `TIMESTAMP, server_default=func.now()` | YES |
| UNIQUE | (brand_id, ref_code) | UniqueConstraint in __table_args__ | YES |

### aliases

| Column | Migration | ORM Model | Match? |
|--------|-----------|-----------|--------|
| id | TEXT PK | `ULIDMixin.id` | YES |
| reference_id | FK NOT NULL | `ForeignKey("references.id"), nullable=False` | YES |
| alias_text | TEXT NOT NULL | `Text(), nullable=False` | YES |
| source | TEXT nullable | `Text(), nullable=True` | YES |
| UNIQUE | (alias_text, source) | UniqueConstraint in __table_args__ | YES |
| No timestamps | — | No `created_at` or `updated_at` | YES |

### watch_list_entries

| Column | Migration | ORM Model | Match? |
|--------|-----------|-----------|--------|
| id | TEXT PK | `ULIDMixin.id` | YES |
| watch_list_id | FK NOT NULL | `ForeignKey("watch_lists.id"), nullable=False` | YES |
| reference_id | FK NOT NULL | `ForeignKey("references.id"), nullable=False` | YES |
| created_at | TIMESTAMPTZ DEFAULT NOW() | `TIMESTAMP, server_default=func.now()` | YES |
| UNIQUE | (watch_list_id, reference_id) | UniqueConstraint in __table_args__ | YES |

**ORM parity result: PASS.** All 9 models match Migration 001 on every column, type, constraint, default, and nullable rule. The `role` column uses `Text()` vs `membership_role` ENUM — accepted as CR-02 NOTE (PostgreSQL enforces valid values at DB layer).

---

## 2. Reserved `"references"` Table

### PostgreSQL DDL Compilation Evidence

```sql
-- Reference.__tablename__ is "references" (without quotes)
-- SQLAlchemy PostgreSQL compiler output:
CREATE TABLE "references" (
    id TEXT
)
```

**Result:** SQLAlchemy correctly wraps the table name in double quotes in generated SQL. PostgreSQL treats `references` as an identifier (not the SQL keyword) when quoted. The ORM safely maps to the existing `"references"` table.

### Model Verification

```python
Reference.__tablename__ == "references"  # True
Reference.__table__.name == "references"  # True (SQLAlchemy stores it unquoted)
# DDL generation adds double quotes automatically
```

**Reserved `"references"` compilation result: PASS.** SQLAlchemy quotes the table name correctly in PostgreSQL DDL output.

---

## 3. Repository Layer Placement

**Issue CR-10: Concrete repositories in `domain/` directory.** (MAJOR)

### Current Location

```
apps/api/apps/api/identity/domain/repositories.py
apps/api/apps/api/catalog/domain/repositories.py
```

### Layer Violation Analysis

| Repository | Imports SQLAlchemy? | Inherits persistence classes? | Depends on ORM models? | Executes queries? |
|-----------|--------------------|---------------------------|----------------------|--------------------|
| OrganizationRepository | YES (`sqlalchemy.select`) | YES (`BaseRepository`) | YES (`Organization`) | YES |
| UserRepository | YES | YES | YES (`User`) | YES |
| MembershipRepository | YES | YES | YES (`Membership`) | YES |
| BrandRepository | YES | YES | YES (`Brand`) | YES |
| SourceRepository | YES | YES | YES (`Source`) | YES |
| ReferenceRepository | YES | YES | YES (`Reference`) | YES |
| WatchListRepository | YES | YES | YES (`WatchList`) | YES |
| AliasRepository | YES | YES | YES (`Alias`) | YES |

All 8 repositories are concrete infrastructure implementations — they import SQLAlchemy, inherit from `BaseRepository`/`TenantRepository`, depend on ORM models, and execute persistence queries. Under the layer dependency rules established in the week-02-domain-plan.md §5.1:

> **Domain** — Pure business rules, policies, formulas. No I/O, no framework deps. Depends on packages/domain-python only.
> **Infrastructure** — SQLAlchemy models, repositories, database sessions, external gateways.

Placing these repositories in `domain/` violates the architecture: domain should have zero dependencies on infrastructure.

### ARG-07 Dependency Enforcement

The `.importlinter` contract `chronoarb-adapter-isolation` forbids `apps.api` imports from domain, but repositories import FROM `apps.api.*` models — they are infrastructure code. If `domain/` is truly domain layer, these imports would violate the dependency rules.

### Recommended Target Paths

```
apps/api/apps/api/identity/infrastructure/repositories.py
apps/api/apps/api/catalog/infrastructure/repositories.py
```

**Repository layer-placement result: FAIL — CR-10 must be fixed before Phase 3.**

---

## 4. Repository Inventory

### Plan vs Implementation

| Plan Entry | Implemented? | Location |
|-----------|-------------|----------|
| OrganizationRepository | YES | identity/domain/repositories.py |
| UserRepository | YES | identity/domain/repositories.py |
| MembershipRepository | YES | identity/domain/repositories.py |
| BrandRepository | YES | catalog/domain/repositories.py |
| ReferenceRepository | YES | catalog/domain/repositories.py |
| WatchListRepository | YES | catalog/domain/repositories.py |
| SourceRepository | YES | catalog/domain/repositories.py |
| AliasRepository | YES | catalog/domain/repositories.py |
| **Total planned: 19** (full Week 2) | **8 implemented** (Phase 2 identity + catalog) | — |

Note: The plan lists 19 repositories total across all Week 2 phases. Phase 2 covers identity + catalog = 8 repositories. The remaining 11 are for Phase 3 (listings, valuation, opportunities, alerts, feedback, billing, operations).

**Repository inventory result: PASS — all 8 Phase 2 repositories are implemented.**

---

## 5. Tenant Isolation

### Tenant-Scoped Repositories

| Repository | Tenant Model? | organization_id Required? | Cross-Tenant Test | Result |
|-----------|-------------|-------------------------|-------------------|--------|
| MembershipRepository | YES | YES — `organization_id` param on `get_by_user_and_org` and `list_members` | `test_membership_cross_tenant_returns_none` passes | PASS |
| WatchListRepository | YES | YES — `list_by_org(organization_id=...)` from TenantRepository | `test_watchlist_tenant_isolation` passes | PASS |

### Global Repositories (Correctly Unscoped)

| Repository | Tenant Scoping? | Assessment |
|-----------|----------------|------------|
| OrganizationRepository | No | Correct — organizations are global identity |
| UserRepository | No | Correct — users are global identity |
| BrandRepository | No | Correct — brands are global catalog |
| SourceRepository | No | Correct — sources are platform-global |
| ReferenceRepository | No | Correct — references are global catalog |
| AliasRepository | No | Correct — aliases are global catalog |

**WatchListEntry:** Currently accessed through `WatchList.entries` relationship (ORM-level). The plan delegates WatchListEntry access to WatchListRepository (which covers both tables). Tenant isolation for entries is enforced by WatchList's `organization_id` — entries cannot exist without a parent WatchList that is already tenant-scoped. No dedicated WatchListEntryRepository is needed per the plan.

**Tenant isolation result: PASS.**

---

## 6. Query Correctness

| Method | Query | Analysis |
|--------|-------|----------|
| `get_by_slug(slug)` | `WHERE slug = slug` | Correct. `slug` has `UNIQUE` constraint — `scalar_one_or_none()` is safe. |
| `get_by_cognito_sub(sub)` | `WHERE cognito_sub = sub` | Correct. Has `UNIQUE` constraint. |
| `get_by_email(email)` | `WHERE email = email` | Correct. Has `UNIQUE` constraint. |
| `get_by_user_and_org(user_id, org_id)` | `WHERE user_id = $1 AND org_id = $2` | Correct. Composite filter with UNIQUE backing. |
| `list_members(org_id)` | `WHERE organization_id = $1` | Correct. Returns all members for org. |
| `get_by_name(name)` | `WHERE name = name` | Correct. Has `UNIQUE` constraint. |
| `get_by_slug(slug)` | `WHERE slug = slug` | Correct. Has `UNIQUE` constraint. |
| `get_by_brand_and_ref_code(brand_id, ref_code)` | `WHERE brand_id = $1 AND ref_code = $2` | Correct. Backed by `UNIQUE(brand_id, ref_code)`. |
| `find_by_alias_text(alias_text)` | `WHERE alias_text = alias_text` | Correct. Returns list — aliases are not unique by text alone (UNIQUE is on text+source). `scalar_one_or_none()` would error on duplicates. Using `list` is correct. |

**Case sensitivity:** All queries use exact string matching (no `ilike`, no `lower()`). This is deliberate — migration 001 uses standard TEXT columns without case-insensitive indexes. Case normalization is an application-layer concern.

**Query correctness result: PASS.** No speculative business rules. Scalar methods use `scalar_one_or_none()` only where UNIQUE constraints guarantee at most one result. `find_by_alias_text` correctly returns a list.

---

## 7. PostgreSQL and SQLite Type Behavior

### JSONB Variants

| Column | PostgreSQL DDL | SQLite DDL | Test Verified? |
|--------|---------------|-----------|----------------|
| Organization.settings | `JSONB` | `JSON` | YES — `test_persist_and_reload_settings` |
| Source.rate_policy | `JSONB` | `JSON` | YES — `test_source_rate_policy_compiles_to_jsonb` |
| Reference.attributes | `JSONB` | `JSON` | YES — `test_reference_attributes_compiles_to_jsonb` |

### is_active / is_enabled Server Defaults

| Column | Python Default | server_default | PostgreSQL Compilation | SQLite Behavior |
|--------|---------------|---------------|----------------------|-----------------|
| Reference.is_active | `default=True` | `sa.text("true")` | `DEFAULT true` | Python default applies; server_default is PostgreSQL DDL metadata |
| Source.is_enabled | `default=False` | `sa.text("false")` | `DEFAULT false` | Python default applies |

**SQLite limitation:** `sa.text("true")` is PostgreSQL-specific syntax. SQLite does not use `server_default` at runtime — it applies the Python-level `default=` instead. The migration DDL is correct (PostgreSQL creates `DEFAULT true`). The ORM model correctly falls back to Python defaults on SQLite.

**Type behavior result: PASS.** JSONB variants compile correctly. Boolean server defaults use Python-level fallbacks for SQLite compatibility.

---

## 8. Relationship Behavior

| Relationship | FK Path | Ambiguity Resolved? | Eager Loading? | Cascade? |
|-------------|---------|--------------------|---------------|----------|
| Organization → Membership | `Membership.organization_id` | N/A — 1 FK to orgs | No (default lazy) | No |
| User → Membership | `Membership.user_id` | YES — `foreign_keys="Membership.user_id"` | No (default lazy) | No |
| Brand → Reference | `Reference.brand_id` | N/A — 1 FK to brands | No (default lazy) | No |
| Reference → Alias | `Alias.reference_id` | N/A — 1 FK to references | No (default lazy) | No |
| WatchList → WatchListEntry | `WatchListEntry.watch_list_id` | N/A — 1 FK | No (default lazy) | No |

**User ↔ Membership FK ambiguity:** The Membership table has two FKs to `users`: `user_id` and `invited_by`. Both relationships correctly resolve the ambiguity:
- `User.memberships` → `foreign_keys="Membership.user_id"` (string-based, no runtime import)
- `Membership.user` → `foreign_keys=[user_id]` (local reference)

**No cross-module runtime imports:** All relationship targets use string references (`"Membership"`, `"Reference"`, `"Alias"`, `"WatchListEntry"`). Python's `from __future__ import annotations` enables forward references. The models are in separate files but string targets avoid circular imports.

**Relationship behavior result: PASS.**

---

## 9. Pydantic Schema Completeness

### Identity Schemas

| Schema | Fields | from_attributes | Missing? |
|--------|--------|---------------|----------|
| OrganizationResponse | id, name, slug, created_at, updated_at | YES | `settings` intentionally excluded (internal) |
| UserResponse | id, email, display_name, created_at, updated_at | YES | `cognito_sub` intentionally excluded (auth data) |
| MembershipResponse | id, org_id, user_id, role, invited_by, created_at | YES | None |

### Catalog Schemas

| Schema | Fields | from_attributes | Missing? |
|--------|--------|---------------|----------|
| BrandResponse | id, name, slug, created_at | YES | None |
| SourceResponse | id, source_key, display_name, adapter_version, access_mode, is_enabled, created_at | YES | `rate_policy`, `approval_ref` intentionally excluded (internal) |
| ReferenceResponse | id, brand_id, ref_code, model_name, generation, is_active, created_at | YES | `attributes` intentionally excluded (internal) |
| WatchListResponse | id, org_id, name, created_at | YES | None |
| WatchListEntryResponse | id, watch_list_id, reference_id, created_at | YES | None |

**Request schemas:** Not required for Phase 2. The plan specifies "API-level DTOs for identity, catalog, and opportunity response types." Request schemas are defined when API routes are implemented (Week 3-5).

**Pydantic completeness result: PASS.** All 8 response schemas match the plan. Internal fields (`settings`, `rate_policy`, `attributes`, `cognito_sub`, `approval_ref`) are correctly excluded from public API responses.

---

## 10. Test Quality

### Test Count

```
API tests:     57 (10 health + 19 infrastructure + 20 catalog + 8 infra guards/org settings/FK)
Domain tests:  33 (money + ULID)
Total:         90
```

### Coverage by Category

| Category | Tests | Examples |
|----------|-------|----------|
| ORM parity | 14 | Table names, UNIQUE constraints, server_defaults |
| PostgreSQL compilation | 2 | JSONB variants for Source.rate_policy, Reference.attributes |
| Identity repos | 4 | Org CRUD, user lookup, membership lookup, cross-tenant |
| Catalog repos | 3 | Brand lookup, reference lookup, watchlist tenant isolation |
| FK enforcement | 3 | Orphan WL, WLE, alias — all rejected |
| Schemas | 2 | ORM-to-response conversion, hidden field exclusion |

### What SQLite Cannot Validate

| Behavior | SQLite | PostgreSQL (CI) |
|----------|--------|-----------------|
| ENUM type enforcement (role) | Stores any string | Rejects invalid values |
| JSONB operators (settings->>'key') | Not available | Works |
| `server_default=sa.text("true")` | Ignored at runtime | Correct DDL |
| RETURNING clause for defaults | Not supported | Works |

All PostgreSQL-specific behaviors are documented as CI validation requirements. No test claims SQLite validates what it cannot.

**Test quality result: PASS.** 90 tests, zero failures, comprehensive coverage.

---

## 11. Scope Compliance

| Concern | Status |
|---------|--------|
| Application services | NOT created — confirmed |
| API routes | NOT created — confirmed |
| Migration 002 models | NOT created — confirmed |
| Workers | NOT created — confirmed |
| Migration changes | NOT created — confirmed |
| Unrelated refactoring | NOT performed — confirmed |

**Scope compliance result: PASS.**

---

## 12. Correction Summary

| ID | Severity | Description | Action |
|----|----------|-------------|--------|
| CR-10 | MAJOR | Repositories in `domain/` — must be in `infrastructure/` | **RESOLVED** — files moved, imports updated, domain/ verified clean |
| CR-02 | NOTE | Membership.role uses Text() not ENUM | Accepted — DB-enforced, Python guard in Phase 3 |
| CR-11 | NOTE | Alias model has no `created_at` field | Correct — matches migration 001 (aliases have no timestamp columns) |
| CR-12 | NOTE | `server_default=sa.text("true")` is PostgreSQL-specific | Python `default=True` ensures correct behavior on SQLite; PostgreSQL DDL is correct |

---

## Final Verdict

### APPROVED WITH CORRECTIONS

| Result | Grade |
|--------|-------|
| ORM parity | PASS — 9 models, zero column or constraint drift from Migration 001 |
| Reserved `"references"` | PASS — SQLAlchemy compiles to `"references"` on PostgreSQL |
| Repository layer placement | **RESOLVED (CR-10)** | Files moved from `domain/` to `infrastructure/` |

---

## 13. CR-10 Resolution (2026-08-03T19:20:05+05:00)

### Old Paths

```
apps/api/apps/api/identity/domain/repositories.py
apps/api/apps/api/catalog/domain/repositories.py
```

### New Paths

```
apps/api/apps/api/identity/infrastructure/repositories.py
apps/api/apps/api/catalog/infrastructure/repositories.py
```

### Imports Updated

| File | Change |
|------|--------|
| `apps/api/tests/test_catalog.py` | 6 imports: `identity.domain.repositories` → `identity.infrastructure.repositories`, `catalog.domain.repositories` → `catalog.infrastructure.repositories` |

### Architectural Boundary Evidence

| Check | Result |
|-------|--------|
| `grep -r "identity\.domain\.repositories" apps/` | 0 matches — no stale imports |
| `grep -r "catalog\.domain\.repositories" apps/` | 0 matches — no stale imports |
| `grep -r "sqlalchemy\|BaseRepository\|TenantRepository" identity/domain/` | 0 files with persistence deps |
| `grep -r "sqlalchemy\|BaseRepository\|TenantRepository" catalog/domain/` | 0 files with persistence deps |
| `ls identity/domain/` | Only `__init__.py` (empty) |
| `ls catalog/domain/` | Only `__init__.py` (empty) |

### Test Results

```
API tests:      57 passed
Domain tests:   33 passed
Total:          90 passed
```

Zero failures. Zero behavior changes.

---

## Final Verdict

### PHASE 2 CLOSED — READY FOR PHASE 3
| Repository inventory | PASS — 8/8 Phase 2 repositories implemented |
| Tenant isolation | PASS — cross-tenant lookups return None |
| Query correctness | PASS — all 10 methods correct |
| JSONB type behavior | PASS — 3 variants compile to JSONB on PostgreSQL |
| Relationship behavior | PASS — FK ambiguity resolved, no cross-module imports |
| Pydantic completeness | PASS — 8 response schemas, internal fields hidden |
| Test quality | PASS — 90 tests, 0 failures |
| Scope compliance | PASS — no Phase 3 code introduced |
