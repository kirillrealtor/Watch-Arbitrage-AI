# Week 02 Phase 01 — Closure Review

**Review type:** Correction verification and final progression gate
**Date:** 2026-08-03T18:40:00+05:00
**Reviewer:** Architecture review pass
**Status:** PENDING — MAJOR finding
**Cross-referenced:** Migration 001 DDL, database-design.md §2.1, phase-01-review.md correction resolution

---

## Executive Summary

All six corrections (CR-01/04/05/06/07/08) are implemented and verified. Repository guards reject null sessions. TenantRepository rejects non-tenant models. UnitOfWork guards prevent misuse outside `async with`. FK enforcement is active via PRAGMA. The `settings` column compiles to PostgreSQL `JSONB` matching migration 001 exactly. 62 tests pass with no failures.

**Verdict: PHASE 1 CLOSED — READY FOR PHASE 2**

---

## 1. Organization.settings Schema Parity

### Migration 001 DDL

```sql
CREATE TABLE organizations (
    ...
    settings JSONB,
    ...
);
```

**Type:** `postgresql.JSONB()` — PostgreSQL binary JSON with indexing support.

### ORM Model Column

```python
settings: Mapped[dict | None] = mapped_column(JSON(), nullable=True)
```

**Type:** `sqlalchemy.JSON()` — generic JSON type.

### PostgreSQL Compilation Test

```sql
-- JSON() compiles to:
CREATE TABLE test (settings JSON)

-- JSONB() compiles to:
CREATE TABLE test2 (settings JSONB)
```

**Issue CR-08: `JSON()` compiles to `JSON` not `JSONB` on PostgreSQL.** (MAJOR)

`sqlalchemy.JSON()` renders as `JSON` on PostgreSQL 17. Migration 001 explicitly uses `postgresql.JSONB()`. These are different types:

| Attribute | `JSON` | `JSONB` |
|-----------|--------|---------|
| Storage | Text (whitespace preserved) | Binary (deduplicated keys) |
| Indexing | No index support | GIN index support |
| Operators | No JSON operators | `->`, `->>`, `@>`, `?` operators |
| Performance | Slower queries | Faster queries |
| Migration match | **No** | **Yes** |

**Impact:**
- `Base.metadata.create_all()` against PostgreSQL creates `JSON` columns where migration DDL created `JSONB` columns
- Schema comparison tools (e.g., `alembic check`, `migra`) would report column type drift
- JSON operators (`settings->>'timezone'`) would fail on `JSON` columns
- Silent degradation: queries work but with worse performance and no index support

**Fix:**
```python
from sqlalchemy.dialects.postgresql import JSONB

settings: Mapped[dict | None] = mapped_column(
    JSON().with_variant(JSONB(), "postgresql"), nullable=True
)
```

This compiles to `JSON` on SQLite (preserving test compatibility) and `JSONB` on PostgreSQL (matching migration 001).

### Nullability and Default

| Attribute | Migration 001 | ORM Model | Match? |
|-----------|-------------|-----------|--------|
| Nullability | `nullable=True` | `nullable=True` | YES |
| Default | None (no `server_default`) | None | YES |

**PASS on nullability/default — CR-08 is type mismatch only.**

---

## 2. Repository Session Guards

### BaseRepository

```python
def __init__(self, session: AsyncSession | None = None) -> None:
    if session is None:
        raise TypeError(
            f"{type(self).__name__} requires a session. "
            "Provide session= directly or use UnitOfWork.repository()."
        )
```

| Test | Result |
|------|--------|
| `BaseRepository()` (no args) | `TypeError` — "requires a session" |
| `BaseRepository(session=valid_session)` | Accepted |
| Error message is descriptive | YES — names the class, suggests alternatives |

### TenantRepository

```python
if session is None:
    raise TypeError(...)  # Inherited from BaseRepository guard
```

| Test | Result |
|------|--------|
| `TenantRepository[TenantModel]()` (no args) | `TypeError` — "requires a session" |
| `TenantRepository[TenantModel](session=valid_session)` | Accepted |

**PASS — guards are active with clear messages.**

---

## 3. TenantRepository Model Enforcement

### Non-Tenant Model Rejection

```python
if model_cls is not None and "organization_id" not in model_cls.__table__.columns:
    raise TypeError(...)
```

| Test | Result |
|------|--------|
| `TenantRepository(NonTenantModel, session, model_cls=NonTenantModel)` | `TypeError` — "organization_id" in message |
| `TenantRepository(TenantModel, session, model_cls=TenantModel)` | Accepted |
| `TenantRepository(TenantModel, session)` (omit model_cls) | Accepted — validation is advisory, not mandatory |

**Issue CR-09: `model_cls` parameter is optional — validation can be bypassed by omitting it.** (NOTE)

If a developer writes `TenantRepository[NonTenantModel](session)` without `model_cls=`, the guard is skipped. The tenant lookup will then silently return `None` for all queries (matching the original CR-05 behavior). This is a tradeoff: mandatory validation at construction time would break existing code that constructs `TenantRepository` without `model_cls=`.

**Action:** Document that `model_cls` should always be provided to `TenantRepository` for tenant validation. The existing test `test_tenant_repo_rejects_non_tenant_model` demonstrates the correct usage pattern.

### Cross-Tenant Isolation

| Test | Result |
|------|--------|
| Create for org_a, query with org_a | Found |
| Create for org_a, query with org_b | `None` |
| Create 3× org_a + 1× org_b, list org_a | 3 results, all org_a |
| Nonexistent ID | `None` |

**PASS — cross-tenant isolation is correct.**

---

## 4. UnitOfWork Semantics

### Guard Verification

| Test | Result |
|------|--------|
| `uow.commit()` outside context | `RuntimeError` — "no active session" |
| `uow.rollback()` outside context | `RuntimeError` — "no active session" |
| `uow.commit()` with injected session | Success — commits without error |

### Lifecycle Verification

| Phase | Implementation | Assessment |
|-------|---------------|------------|
| `__aenter__` | Creates session if none provided | Correct |
| `commit()` | Guarded — raises if no session | Correct |
| `rollback()` | Guarded — raises if no session | Correct |
| `__aexit__` | Closes session if owned, does NOT commit/rollback | Correct — explicit commit required |
| `repository()` factory | `repo_cls(self.session)` — same session | Correct |
| No double-commit guard | Calling `commit()` twice would succeed twice — second is a no-op | Acceptable |

**Finding:** The UoW correctly requires explicit `commit()`. Forgetting to call `commit()` silently discards changes at `__aexit__` close. This is documented behavior — the caller is responsible for committing or rolling back.

**PASS — guards are active, lifecycle is correct.**

---

## 5. Foreign-Key Test Enforcement

### PRAGMA Configuration

```python
@event.listens_for(engine.sync_engine, "connect")
def enable_fks(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

| Check | Result |
|-------|--------|
| PRAGMA fires on every connection | YES — `event.listen` with `"connect"` event |
| FK rejection test passes | YES — orphan Membership raises `IntegrityError` |
| Test cleanup doesn't mask failures | Each test uses isolated in-memory database (`sqlite+aiosqlite://`) |

**PASS — FK enforcement is active and verified.**

---

## 6. Identity Model Parity

### Column-by-Column Comparison Against Migration 001

**organizations:**

| Column | Migration | ORM Model | Match? |
|--------|-----------|-----------|--------|
| `id` | TEXT PK | `ULIDMixin.id` (Text PK) | YES |
| `name` | TEXT NOT NULL | `Text(), nullable=False` | YES |
| `slug` | TEXT UNIQUE NOT NULL | `Text(), unique=True, nullable=False` | YES |
| `settings` | `JSONB` | `JSON().with_variant(JSONB(), "postgresql")` — compiles to JSONB on PostgreSQL, JSON on SQLite | **YES (CR-08 resolved)** |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | `TimestampMixin.created_at` | YES |
| `updated_at` | TIMESTAMPTZ DEFAULT NOW() | `TimestampMixin.updated_at` | YES |

**users:**

| Column | Migration | ORM Model | Match? |
|--------|-----------|-----------|--------|
| `id` | TEXT PK | `ULIDMixin.id` | YES |
| `cognito_sub` | TEXT UNIQUE NOT NULL | `Text(), unique=True, nullable=False` | YES |
| `email` | TEXT UNIQUE NOT NULL | `Text(), unique=True, nullable=False` | YES |
| `display_name` | TEXT | `Text(), nullable=True` | YES |
| `created_at` | TIMESTAMPTZ | `TimestampMixin.created_at` | YES |
| `updated_at` | TIMESTAMPTZ | `TimestampMixin.updated_at` | YES |

**memberships:**

| Column | Migration | ORM Model | Match? |
|--------|-----------|-----------|--------|
| `id` | TEXT PK | `ULIDMixin.id` | YES |
| `organization_id` | FK NOT NULL | `ForeignKey("organizations.id"), nullable=False` | YES |
| `user_id` | FK NOT NULL | `ForeignKey("users.id"), nullable=False` | YES |
| `role` | `membership_role` ENUM | `Text(), nullable=False` | NOTE (CR-02, accepted) |
| `invited_by` | FK nullable | `ForeignKey("users.id"), nullable=True` | YES |
| `created_at` | TIMESTAMPTZ | `TIMESTAMP(timezone=True), server_default=func.now()` | YES |
| UNIQUE(user_id, org_id) | — | `UniqueConstraint` in `__table_args__` | YES |

### Relationships

| Model | Relationship | Foreign Key | Correct? |
|-------|-------------|------------|----------|
| Organization | `memberships` → Membership | `Membership.organization_id` | YES — unambiguous (1 FK to orgs) |
| User | `memberships` → Membership | `Membership.user_id` | YES — `foreign_keys="Membership.user_id"` resolves ambiguity vs invited_by |
| Membership | `organization` → Organization | `organization_id` | YES |
| Membership | `user` → User | `user_id` | YES — `foreign_keys=[user_id]` resolves ambiguity |

**PASS — all identity columns and relationships match, excluding CR-02 (role Text) and CR-08 (settings JSON).**

---

## 7. Test Quality

### Test Suite Breakdown

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestBaseRepository` | 4 | CRUD on generic model |
| `TestTenantRepository` | 4 | Tenant isolation (get, cross, list, nonexistent) |
| `TestRepositorySessionGuard` | 4 | Session=None rejection (base, tenant, non-tenant model, tenant model) |
| `TestUnitOfWorkGuards` | 4 | Commit/rollback guards, within-context, rollback |
| `TestOrganizationSettings` | 2 | Settings round-trip, nullable |
| `TestForeignKeyEnforcement` | 1 | Orphan Membership rejection |
| `TestHealthEndpoint` (test_health.py) | 4 | Health endpoint |
| `TestReadyEndpoint` (test_health.py) | 2 | Ready endpoint |
| `TestErrorHandling` (test_health.py) | 2 | 422/404 error handling |
| `TestTraceIdPropagation` (test_health.py) | 2 | Trace ID on all responses |
| **Subtotal (API)** | **29** | |
| Domain tests (money + ULID) | 33 | |
| **Total** | **62** | |

### Test Quality Assessment

| Metric | Assessment |
|--------|------------|
| Tests assert observable behavior | YES — no tests assert `__dict__` internals or implementation details |
| Error messages checked for clarity | YES — `match="requires a session"`, `match="organization_id"` |
| Edge cases covered | YES — None sessions, non-tenant models, outside context, orphan FKs |
| Test isolation | YES — `sqlite+aiosqlite://` per test, engine disposed after each |
| FK enforcement verified | YES — integration test proves SQLite rejects orphan rows |
| No mocks used | YES — all tests use real SQLAlchemy engines and sessions |

**PASS — 62 tests, all pass, no flaky tests, no implementation-detail assertions.**

---

## 8. Correction Status

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| CR-01 | MAJOR | Organization missing `settings` column | **RESOLVED** — column added |
| CR-02 | NOTE | Membership `role` Text vs ENUM | **DEFERRED** — DB-enforced |
| CR-04 | MINOR | Repository session=None guard | **RESOLVED** — TypeError raised |
| CR-05 | MINOR | TenantRepository non-tenant model guard | **RESOLVED** — TypeError raised (advisory) |
| CR-06 | MINOR | UoW commit/rollback guard | **RESOLVED** — RuntimeError raised |
| CR-07 | MAJOR | SQLite FK enforcement | **RESOLVED** — PRAGMA active |
| CR-08 | MAJOR | `JSON()` → `JSON` not `JSONB` on PostgreSQL | **RESOLVED** — `JSON().with_variant(JSONB(), "postgresql")` |
| CR-09 | NOTE | `model_cls` optional on TenantRepository | **DEFERRED** — document convention |

---

## 9. CR-08 Resolution (2026-08-03T18:48:08+05:00)

### Previous Mapping

```python
from sqlalchemy import JSON
settings: Mapped[dict | None] = mapped_column(JSON(), nullable=True)
```

Compiled to `JSON` on both PostgreSQL and SQLite. Mismatch with migration 001 which uses `postgresql.JSONB()`.

### Corrected Mapping

```python
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
settings: Mapped[dict | None] = mapped_column(
    JSON().with_variant(JSONB(), "postgresql"), nullable=True
)
```

### PostgreSQL Compiled Type Evidence

```sql
-- Python: JSON().with_variant(JSONB(), "postgresql")
-- PostgreSQL compilation: CREATE TABLE test (settings JSONB)
```

**Result: JSONB** — matches migration 001 `sa.Column("settings", postgresql.JSONB(), nullable=True)`.

### SQLite Compatibility Evidence

```sql
-- SQLite compilation: CREATE TABLE test (settings JSON)
```

**Result: JSON** — SQLite stores as TEXT, dict round-trips preserve structure identically to JSONB.

### Test Evidence

| Test | Result |
|------|--------|
| `test_persist_and_reload_settings` — dict `{"timezone":"UTC","default_currency":"USD"}` round-trips correctly | PASS |
| `test_settings_nullable` — Organization created without `settings` has `settings is None` | PASS |
| Full API test suite (29 tests) | PASS |
| Full domain test suite (33 tests) | PASS |
| **Total** | **62 PASS** |

---

## 10. Final Verdict

### PHASE 1 CLOSED — READY FOR PHASE 2

CR-08 resolved. PostgreSQL JSONB parity achieved. All 62 tests pass.

### UnitOfWork Lifecycle Result

**PASS.** Guards prevent misuse. Explicit commit required. Sessions are closed on `__aexit__` when owned. Repository factory shares the active session.

### Tenant Isolation Result

**PASS.** Cross-tenant queries return `None`. `list_by_org` returns only matching organization rows. TenantRepository rejects non-tenant models (advisory guard). Tenant views cannot see other organizations' data.

### Final Test Count

**62 tests** (29 API + 33 domain). All pass.

### Remaining Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| CR-08: JSON/JSONB mismatch | MAJOR | Fix with `JSON().with_variant(JSONB(), "postgresql")` before Phase 2 |
| CR-02: `role` Text vs ENUM | NOTE | PostgreSQL enforces at DB layer; Python-level guard in Phase 2 |
| CR-09: `model_cls` optional on TenantRepository | NOTE | Document convention; test demonstrates correct usage |
| `Updated_at` uses Python lambda only | NOTE | No `server_default` on `updated_at` in mixin — rely on `onupdate` lambda |
| `References` reserved word | NOTE | Double-quoting needed in raw SQL; ORM handles transparently |
