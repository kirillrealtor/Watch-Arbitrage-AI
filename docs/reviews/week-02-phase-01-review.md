# Week 02 Phase 01 — Implementation Review

**Review type:** Post-implementation architecture audit
**Reviewed files:** 6 files (models, repository, uow, identity models, tests)
**Date:** 2026-08-03T18:07:02+05:00
**Reviewer:** Architecture review pass
**Cross-referenced:** Migration 001 DDL, database-design.md §2.1, AGENTS.md

---

## Executive Summary

Phase 1 delivers working `BaseRepository`, `TenantRepository`, and `UnitOfWork` abstractions with 8 passing tests and correct tenant isolation behavior. The ORM model patterns (ULIDMixin, TimestampMixin, TenantMixin) are clean and reusable. However, the `Organization` model is missing the `settings` column from migration 001, which would cause a runtime error if the column is accessed or if `Base.metadata.create_all()` is compared against the migration schema. Additionally, SQLite tests do not enforce foreign key constraints, which will mask referential integrity bugs until CI PostgreSQL validation.

**Verdict: APPROVED WITH CORRECTIONS**

---

## 1. ORM Models Against Migration 001

### Column-by-Column Migration Alignment

**organizations table (migration 001):**
| Column | Migration Type | Model Column | Present? |
|--------|---------------|-------------|----------|
| `id` | TEXT PK | `ULIDMixin.id` | YES |
| `name` | TEXT NOT NULL | `Mapped[str]`, NOT NULL | YES |
| `slug` | TEXT UNIQUE NOT NULL | `unique=True, nullable=False` | YES |
| `settings` | JSONB | **MISSING** | **NO** |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | `TimestampMixin.created_at` | YES |
| `updated_at` | TIMESTAMPTZ DEFAULT NOW() | `TimestampMixin.updated_at` | YES |

**Issue CR-01: Organization model missing `settings` column.** (MAJOR)

Migration 001 creates `organizations.settings JSONB` — the model has no corresponding column. This means:
- `org.settings` would raise `AttributeError` at runtime
- `Base.metadata.create_all()` would not produce the `settings` column, causing schema drift from migration DDL
- Any organization creation/update that sets `settings` (expected by the API design) would silently discard the value

**Fix:** Add `settings: Mapped[dict | None] = mapped_column(postgresql.JSONB(), nullable=True)` to the Organization model.

**users table (migration 001):**
| Column | Migration Type | Model Column | Present? |
|--------|---------------|-------------|----------|
| `id` | TEXT PK | `ULIDMixin.id` | YES |
| `cognito_sub` | TEXT UNIQUE NOT NULL | `unique=True, nullable=False` | YES |
| `email` | TEXT UNIQUE NOT NULL | `unique=True, nullable=False` | YES |
| `display_name` | TEXT | `nullable=True` | YES |
| `created_at` | TIMESTAMPTZ | `TimestampMixin.created_at` | YES |
| `updated_at` | TIMESTAMPTZ | `TimestampMixin.updated_at` | YES |

**PASS — all columns present.**

**memberships table (migration 001):**
| Column | Migration Type | Model Column | Present? |
|--------|---------------|-------------|----------|
| `id` | TEXT PK | `ULIDMixin.id` | YES |
| `organization_id` | FK NOT NULL | `ForeignKey("organizations.id")` | YES |
| `user_id` | FK NOT NULL | `ForeignKey("users.id")` | YES |
| `role` | membership_role ENUM | `Text(), nullable=False` | YES (type mismatch — see CR-03) |
| `invited_by` | FK nullable | `ForeignKey("users.id"), nullable=True` | YES |
| `created_at` | TIMESTAMPTZ | Direct `mapped_column(TIMESTAMP(...))` | YES |
| UNIQUE(user_id, org_id) | — | `UniqueConstraint` in `__table_args__` | YES |

**Issue CR-02: Membership `role` column modeled as `Text()` but migration uses `membership_role` ENUM.** (NOTE)

PostgreSQL native ENUMs accept only the defined values (`owner`, `admin`, `dealer`, `viewer`). The model using `Text()` allows any string through SQLAlchemy, relying on PostgreSQL to reject invalid values at INSERT time. This is acceptable (database-enforced) but means:
- Application code can construct a `Membership(role="superadmin")` without type-checker errors
- The error surfaces as a database exception, not a type error
- For production, a Python-level validation (Pydantic enum or domain-level guard) should complement the DB constraint

This is a Phase 2 concern — not actionable in Phase 1.

**PASS (with NOTE for Production).**

---

## 2. SQLAlchemy 2.0 Typing and Conventions

| Convention | Status |
|-----------|--------|
| `Mapped[type]` annotations | YES — all columns use `Mapped[str]`, `Mapped[datetime]`, `Mapped[str | None]` |
| `mapped_column()` with explicit types | YES — `Text()`, `TIMESTAMP(timezone=True)`, `ForeignKey()` |
| `__tablename__` matches migration | YES — `"organizations"`, `"users"`, `"memberships"` |
| Mixins (ULID, Timestamp, Tenant) | YES — composition over inheritance, clean separation |
| `relationship()` with `back_populates` | YES — bi-directional relationships on Organization/Membership/User |
| `from __future__ import annotations` | YES — all files |
| `__table_args__` for composite constraints | YES — `UniqueConstraint` on memberships |
| No `server_default` on `updated_at` | Intentional — `onupdate` lambda handles it in Python |

**PASS.**

---

## 3. BaseRepository Correctness

### Method Audit

| Method | Implementation | Assessment |
|--------|---------------|------------|
| `get_by_id(model_cls, id)` | `session.get(model_cls, id)` — PK lookup | Correct. Uses primary key, efficient. |
| `list_all(model_cls, limit, offset)` | `select(model_cls).offset(offset).limit(limit)` | Correct. Basic pagination, no ordering guarantees. |
| `count(model_cls)` | `select(func.count()).select_from(model_cls)` | Correct. Efficient COUNT query. |
| `save(model)` | `session.add(model); session.flush()` | Correct. Flush not commit — caller owns transaction boundary. |
| `delete(model)` | `session.delete(model); session.flush()` | Correct. Same transaction pattern. |

### Design Decisions

| Decision | Assessment |
|----------|------------|
| `model_cls` parameter on every method | Unusual but valid. Requires caller to pass model class each time. Could be simplified by storing `model_cls` in `__init__`. Trade-off: more flexible (one repo instance for multiple model types) vs less ergonomic. → NOTE |
| No `update` method | Intentional — aligns with immutable records pattern (ADR-0001 D10). Updates are done by creating new model instances. |
| `session` optional with `None` default | No guard — `self.session.get(...)` raises `AttributeError` if `session` is None. → MINOR |

**Issue CR-04: `BaseRepository(session=None)` has no guard.** (MINOR)

If a repository is constructed without a session and any method is called, it raises `AttributeError: 'NoneType' object has no attribute 'get'`. A `TypeError` or `ValueError` with a clear message would be more debuggable.

**Fix:** Add `if self.session is None: raise RuntimeError("Repository requires a session")` in `__init__` or at method call time.

**PASS (with MINOR guard note).**

---

## 4. TenantRepository Security

### Cross-Tenant Isolation Audit

| Method | Tenant Check | Assessment |
|--------|-------------|------------|
| `get_by_id(id, organization_id)` | Load model by ID → check `model.organization_id` matches param → return None if mismatch | Correct. Cannot distinguish "doesn't exist" from "wrong tenant." |
| `list_by_org(organization_id)` | `WHERE organization_id = param` | Correct. Database-level filter, no post-filter needed. |

### Edge Case: Non-Tenant Models

**Issue CR-05: `TenantRepository.get_by_id` on non-tenant model returns None silently.** (MINOR)

If `TenantRepository` is used with a model that has no `organization_id` column (e.g., `Brand`, `Reference`), `getattr(model, "organization_id", None)` returns `None`. The comparison `None != organization_id` is `True`, so the method returns `None` — even though the model was found and the org_id comparison was meaningless.

**Fix:** Raise `TypeError` if the model class has no `organization_id` column. The check: `if "organization_id" not in model_cls.__table__.columns`. This catches misuse at development time rather than silently returning None.

**TenantGuard is correct for tenant models.** The cross-tenant test suite confirms: create for org_a → query with org_b → None.

**PASS (with MINOR guard note).**

---

## 5. UnitOfWork Transaction Semantics

### Lifecycle Audit

| Phase | Implementation | Assessment |
|-------|---------------|------------|
| Construction | `session` or `sessionmaker` passed in | Correct. Supports both injected and auto-created sessions. |
| `__aenter__` | Creates session if none provided | Correct. `async with UnitOfWork() as uow:` works. |
| `commit()` | `await self.session.commit()` | **No None guard** — if called outside `async with`, raises AttributeError. → MINOR |
| `rollback()` | `await self.session.rollback()` | Same None guard issue. |
| `__aexit__` | Closes session if owned, does NOT commit/rollback | Correct. Uncommitted changes are rolled back by session close. Explicit commit required. |
| `repository()` factory | `repo_cls(self.session)` | Correct. Creates repo with UoW's session. |

### Transaction Boundary Enforcement

The UoW does NOT auto-commit in `__aexit__`. The caller must explicitly `await uow.commit()`. This is correct — it prevents accidental commits of partial work. However, it means forgetting `commit()` silently discards changes at session close.

**Issue CR-06: `UnitOfWork.commit()` has no guard against None session.** (MINOR)

**Fix:** Same pattern as CR-04: raise `RuntimeError("Session not initialized — use `async with UnitOfWork()`")` if `self.session is None`.

**PASS (with MINOR guard note).**

---

## 6. Session Lifecycle and Cleanup

### Test Fixture

```python
@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, ...)
    async with sessionmaker() as s:
        yield s
    await engine.dispose()
```

**Assessment:** Correct. Engine created once per test, tables created in a transaction, session yielded, engine disposed. No session leaks. `create_all` runs for each test — scoped isolation.

**Improvement opportunity (Phase 2):** Use `engine.begin()` wrapping `run_sync` for DDL in a single transaction that commits before the test. This is already correct — the `create_all` runs inside `engine.begin()` which auto-commits.

**PASS.**

---

## 7. Foreign-Key Enforcement in Tests

**Issue CR-07: SQLite tests do not enforce foreign keys.** (MAJOR)

SQLite does not enforce foreign key constraints by default. `PRAGMA foreign_keys = ON` must be enabled per-connection. The test fixture creates the engine without this pragma.

**Impact:**
- Inserting a `Membership` row with a non-existent `organization_id` would succeed on SQLite but fail on PostgreSQL
- FK constraint violations would go undetected in local development
- CI (PostgreSQL on Python 3.13 leg) would catch them, but developers would spend time debugging "works on my machine" issues

**Fix:** Add `event.listen` to enable foreign keys after engine creation:

```python
from sqlalchemy import event

@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def enable_fks(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    ...
```

**Action:** Add FK enforcement to the test fixture before Phase 2. This is a gate-blocker for Phase 2 — without FK enforcement, the test suite cannot validate referential integrity.

---

## 8. UNIQUE Constraint Coverage

| Model | UNIQUE Constraint | Model Match Migration? |
|-------|------------------|----------------------|
| Organization | `slug` — `unique=True` on column | YES — matches `uq_organizations_slug` |
| User | `cognito_sub` — `unique=True` | YES — matches `uq_users_cognito_sub` |
| User | `email` — `unique=True` | YES — matches `uq_users_email` |
| Membership | `(user_id, organization_id)` — `UniqueConstraint` in `__table_args__` | YES — matches `uq_memberships_user_org` |

**PASS — all UNIQUE constraints correctly modeled.**

---

## 9. Dependency-Direction Compliance

| From | To | Allowed? |
|------|----|----------|
| `identity/models.py` | `infrastructure/models.py` | YES — same layer (infrastructure) |
| `infrastructure/repository.py` | `infrastructure/database.py` | YES — same layer |
| `infrastructure/repository.py` | `infrastructure/models.py` | NO — repository does NOT import models. Correct. |
| `infrastructure/uow.py` | `infrastructure/database.py` | YES — same layer |
| `infrastructure/uow.py` | `infrastructure/repository.py` | YES — same layer |
| `infrastructure/__init__.py` | `infrastructure/models.py`, `repository.py`, `uow.py` | YES — same package exports |

**PASS — zero forbidden imports. All dependencies stay within infrastructure layer. No domain-layer violations.**

---

## 10. Test Quality and Missing Failure Paths

### Covered Paths (8 tests)

| Test | Path |
|------|------|
| `test_save_and_get_by_id` | Happy path: create → commit → retrieve |
| `test_list_all` | Pagination: create 5 → list 3 |
| `test_count` | Aggregation: create 3 → count 3 |
| `test_delete` | Deletion: create → delete → verify gone |
| `test_get_by_id_with_matching_org` | Tenant guard: same org → found |
| `test_cross_tenant_returns_none` | Tenant guard: different org → None |
| `test_list_by_org_only_returns_own` | Tenant isolation: mixed orgs → only returns matching |
| `test_nonexistent_id_returns_none` | Edge case: missing ID → None |

### Missing Failure Paths

| Path | Why Missing | Risk |
|------|------------|------|
| `BaseRepository(session=None).get_by_id()` | CR-04 | `AttributeError` at runtime, unclear error message |
| `UoW.commit()` outside `async with` | CR-06 | `AttributeError` at runtime |
| FK constraint violation (orphan Membership) | CR-07 | Tests pass locally, fail in CI PostgreSQL |
| `save()` duplicate UNIQUE key | No test | SQLite silently rolls back, PostgreSQL raises IntegrityError |
| `count()` on empty table | No test | Should return 0 — tests with 3 rows won't catch this |

**Finding:** Basic CRUD covered. Guard conditions and edge cases not covered. Acceptable for Phase 1 infrastructure foundation — Phase 2 domain-specific tests will cover deeper scenarios.

**PASS (with noted gaps for Phase 2).**

---

## 11. SQLite Versus PostgreSQL Behavioral Differences

| Difference | Impact | Mitigation |
|-----------|--------|------------|
| SQLite doesn't enforce FKs by default | FK constraint tests pass locally, fail in CI | CR-07: add PRAGMA foreign_keys=ON |
| SQLite doesn't support ENUM | `role` column stores any string locally, rejected by PostgreSQL | Acceptable — catch at CI; add Python-level ENUM guard in Phase 2 |
| SQLite TEXT vs JSONB | `settings` column stores TEXT not JSONB locally | Acceptable — JSON serialization works the same |
| SQLite doesn't support `server_default=func.now()` | Defaults rely on Python-side `default=` lambda | Acceptable — Python lambda is the primary default; `server_default` is belt-and-suspenders |
| `TIMESTAMP(timezone=True)` becomes TEXT on SQLite | Timestamps stored without timezone info locally | Acceptable — `datetime(timezone.utc)` lambda ensures UTC in Python |

**Finding:** All differences are documented as ADR-0009 coverage. The critical gaps are FK enforcement (CR-07) and the ENUM type mismatch (CR-02, NOTE). Both are mitigated by CI PostgreSQL validation.

**PASS (with FK enforcement correction).**

---

## 12. Correction Summary

| ID | Severity | Description | File | Action |
|----|----------|-------------|------|--------|
| CR-01 | MAJOR | Organization model missing `settings` column | `identity/models.py:13-22` | Add `settings: Mapped[dict \| None] = mapped_column(postgresql.JSONB(), nullable=True)` |
| CR-02 | NOTE | Membership `role` uses Text() not ENUM type | `identity/models.py:48` | Acceptable — PostgreSQL ENUM enforces at DB level; Python-level guard in Phase 2 |
| CR-03 | — | (Reserved for future finding) | — | — |
| CR-04 | MINOR | `BaseRepository(session=None)` has no guard | `repository.py:15-16` | Raise `RuntimeError("Repository requires a session")` if session is None |
| CR-05 | MINOR | `TenantRepository` on non-tenant model returns None silently | `repository.py:50-56` | Add type guard: `if "organization_id" not in model_cls.__table__.columns: raise TypeError(...)` |
| CR-06 | MINOR | `UnitOfWork.commit()` has no guard against None session | `uow.py:28-29` | Raise `RuntimeError` if session is None |
| CR-07 | MAJOR | SQLite tests do not enforce foreign keys | `test_infrastructure.py:24-31` | Add `PRAGMA foreign_keys=ON` in test fixture engine connect listener |

---

## 13. Correction Resolution (2026-08-03T18:20:00+05:00)

| ID | Status | Resolution |
|----|--------|-----------|
| CR-01 | **RESOLVED** | Added `settings: Mapped[dict \| None] = mapped_column(JSON(), nullable=True)` to Organization model. Uses `sqlalchemy.JSON` (not PostgreSQL `JSONB`) for SQLite test compatibility while matching migration DDL behavior. Test confirms round-trip persistence. |
| CR-02 | **DEFERRED** | Membership `role` remains `Text()` — PostgreSQL native ENUM enforces valid values at the database layer. Python-level ENUM guard deferred to Phase 2. |
| CR-04 | **RESOLVED** | `BaseRepository.__init__` raises `TypeError("requires a session")` when session is None. Tests confirm for both BaseRepository and TenantRepository. |
| CR-05 | **RESOLVED** | `TenantRepository.__init__` accepts optional `model_cls` parameter. When provided, validates that `organization_id` exists in the model's table columns. Raises `TypeError` for non-tenant models showing the model name in the message. |
| CR-06 | **RESOLVED** | `UnitOfWork.commit()` and `rollback()` raise `RuntimeError("no active session")` when called outside `async with` context. Tests cover: outside-context rejection, within-context success, and exception-triggered rollback. |
| CR-07 | **RESOLVED** | `PRAGMA foreign_keys=ON` added to test fixture via SQLAlchemy `event.listen` on engine connect. Test confirms invalid Membership FK (nonexistent org/user) is rejected with an exception. |

### Additional Fix Applied

The `User.memberships` relationship now specifies `foreign_keys="Membership.user_id"` to resolve the ambiguity introduced by the Membership table having two foreign keys to `users` (`user_id` and `invited_by`). This was discovered during CR-01 resolution when the `JSONB` → `JSON` change triggered a mapper initialization path that exposed the ambiguity.

### Post-Correction Test Suite

| Suite | Tests | Outcome |
|-------|-------|---------|
| Health endpoint | 10 | PASS |
| Infrastructure (repo + uow + guards) | 11 | PASS |
| Tenant isolation | 4 | PASS |
| Session guards (CR-04/05) | 4 | PASS |
| UoW guards (CR-06) | 4 | PASS |
| Organization settings (CR-01) | 2 | PASS |
| FK enforcement (CR-07) | 1 | PASS |
| Domain (money + ULID) | 33 | PASS |
| **Total** | **62** | **ALL PASS** |

---

## 14. Phase Progression Gate

**Question: Is the implementation ready for Phase 2 (catalog models + additional repositories)?**

Yes, with two required corrections.

| Gate | Status |
|------|--------|
| ORM models match migration 001 | **PENDING CR-01** (Organization missing `settings`) |
| SQLAlchemy 2.0 typing correct | PASS |
| BaseRepository functional | PASS (CR-04 guard recommended) |
| TenantRepository secure | PASS (CR-05 guard recommended) |
| UoW transaction semantics correct | PASS (CR-06 guard recommended) |
| Session lifecycle clean | PASS |
| FK enforcement in tests | **PENDING CR-07** (PRAGMA missing) |
| UNIQUE constraints modeled | PASS |
| Dependency direction clean | PASS |
| Test quality adequate for Phase 1 | PASS |

**Verdict: APPROVED WITH CORRECTIONS**

CR-01 and CR-07 must be fixed before Phase 2 begins. CR-04, CR-05, and CR-06 are recommended quality improvements that can be applied during Phase 2 without blocking progress.
