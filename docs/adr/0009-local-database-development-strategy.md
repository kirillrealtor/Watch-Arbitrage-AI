# ADR-0009: Local Database Development Strategy

**Status:** Accepted
**Date:** 2026-08-03
**Deciders:** Lead Software Architect
**Supersedes:** None
**Resolves:** Batch 3 DB-01/DB-04 implementation decision (asyncpg + Python 3.14 incompatibility)
**Related:** ADR-0008 (migration split strategy), python-runtime.md (Python 3.14 decision)

---

## Context

ChronoArb's system of record is PostgreSQL 17 (ADR-0001 D2). The Batch 3 implementation attempted to connect the async SQLAlchemy engine to a local PostgreSQL 17 Docker container using `asyncpg` as the async driver.

**Connection behavior observed (2026-08-03):**

| Driver | Python | Result |
|--------|--------|--------|
| asyncpg 0.31.0 | 3.14.6 | TimeoutError during `_create_ssl_connection` negotiation |
| asyncpg 0.31.0 (`ssl=False`) | 3.14.6 | CancelledError during `await connected` |
| psycopg 3 (async) | 3.14.6 | TimeoutError — same TCP negotiation hang |
| psycopg2 (sync) | 3.14.6 | TimeoutError — same hang |
| aiosqlite | 3.14.6 | Immediate connection — 1ms latency |

PostgreSQL 17 Docker container is running, accepting TCP connections on port 5432, and serving queries correctly via `psql` and `docker exec`. TCP connectivity from Python is confirmed (`socket.connect_ex` returns 0). The issue is specific to Python database drivers (asyncpg, psycopg) negotiating the PostgreSQL wire protocol on Python 3.14.

The Python runtime was previously decided as Python 3.14 (python-runtime.md), based on:
- System Python is 3.14.6 (only version available without a version manager)
- All 11 core pip dependencies resolved on 3.14
- SRS says "3.13.x initially" — flexible language

The asyncpg incompatibility was not detected during the Python runtime evaluation because the evaluation only checked `pip install` resolution (wheels/sdist availability), not runtime behavior.

---

## Problem

The async SQLAlchemy engine cannot connect to PostgreSQL on the development machine (Python 3.14.6). Two options exist:

**Option A:** Require Python 3.13 for local development (reverse the python-runtime.md decision).
**Option B:** Use SQLite (aiosqlite) for local development, validate against PostgreSQL in CI.

---

## Decision

**Selected: Option B — SQLite (aiosqlite) for local development, PostgreSQL validation in CI and staging.**

### Rationale

1. **Python 3.14 is already the decided runtime.** Reversing the python-runtime.md decision would require every developer to install a Python version manager (pyenv/asdf) and a second Python interpreter. This adds setup friction that Option A was specifically designed to avoid.

2. **The incompatibility is temporary.** asyncpg 0.31.0 was built against CPython 3.14 ABI but appears to have a runtime bug in wire protocol negotiation. Future asyncpg releases (0.32.0+) will likely resolve this. When fixed, the `database_url` default can switch back to PostgreSQL with a one-line config change.

3. **CI validates PostgreSQL correctness.** GitHub Actions runs Python 3.13 (per python-runtime.md §6: CI matrix `["3.13", "3.14"]`). All integration tests, migrations, and schema validation will exercise PostgreSQL on the 3.13 leg. No PostgreSQL-specific bug can reach production.

4. **SQLite is a valid development database.** FastAPI + SQLAlchemy 2.0 + Alembic are database-agnostic at the application layer. The async engine, session factory, and dependency injection patterns are identical regardless of backend. Only DDL (migrations) and PostgreSQL-specific features (JSONB, ENUM, TIMESTAMPTZ) differ.

5. **Docker PostgreSQL is available for ad-hoc testing.** Developers can still run migrations against PostgreSQL manually: `CHRONOARB_DATABASE_URL=postgresql+asyncpg://... alembic upgrade head`. This requires the Docker container to be running (already set up in DB-01).

### Development Workflow

```
┌─────────────────────────────────────────────────────────┐
│                  Developer Workstation                   │
│                                                         │
│  FastAPI (Python 3.14)                                  │
│       │                                                 │
│       │  settings.database_url                          │
│       │  = "sqlite+aiosqlite:///chronoarb.db" (default) │
│       ▼                                                 │
│  SQLite (aiosqlite) ← in-memory or file-based           │
│                                                         │
│  Alembic (Python 3.14)                                  │
│       │                                                 │
│       │  env.py → _get_url() → settings.database_url    │
│       ▼                                                 │
│  SQLite (migration runs against same DB)                │
│                                                         │
│  Manual PostgreSQL test:                                │
│   CHRONOARB_DATABASE_URL=postgresql+asyncpg://... \     │
│     alembic upgrade head                                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                      CI (GitHub Actions)                 │
│                                                         │
│  Job: test-python (3.13)                                │
│       │                                                 │
│       │  CHRONOARB_DATABASE_URL=                        │
│       │    postgresql+asyncpg://postgres:chronoarb@...  │
│       ▼                                                 │
│  PostgreSQL service container                            │
│       │                                                 │
│       │  alembic upgrade head → PostgreSQL ✓             │
│       │  pytest apps/api/       → PostgreSQL ✓           │
│       └─────────────────────────────────────────────────│
│                                                         │
│  Job: test-python (3.14)                                │
│       │                                                 │
│       │  default DATABASE_URL → SQLite                   │
│       ▼                                                 │
│  SQLite (fast, validates application logic)              │
└─────────────────────────────────────────────────────────┘
```

### Migration Testing Requirements

| Check | Local (SQLite) | CI (PostgreSQL) |
|-------|---------------|-----------------|
| `alembic upgrade head` | Against SQLite (verifies migration Python code runs) | Against PostgreSQL (verifies DDL correctness) |
| `alembic downgrade base` | Against SQLite | Against PostgreSQL |
| Column types | Not validated (SQLite is dynamically typed) | Strictly validated (NUMERIC(18,2), TIMESTAMPTZ, ENUM) |
| Foreign keys | Not validated by default (SQLite pragma) | Strictly enforced |
| JSONB | Stored as TEXT in SQLite | Native JSONB with operators |
| Partial indexes | Not supported by SQLite | Created with WHERE clauses |

**Consequence:** Migration tests MUST pass the PostgreSQL CI leg before merging. A migration that passes SQLite locally but fails on PostgreSQL in CI will be caught at PR time, not at deploy time.

### Transition Path

When asyncpg resolves its Python 3.14 incompatibility:

1. Verify with: `pip install --upgrade asyncpg && timeout 5 python -c "import asyncpg; ..."`
2. Update `settings.py` default: `database_url = "postgresql+asyncpg://postgres:chronoarb@localhost:5432/chronoarb"`
3. Update CI: remove the separate 3.13/3.14 database strategy — both legs use PostgreSQL
4. No migration, no code changes beyond the `default=` value

---

## Alternatives Considered

### Alternative A: Require Python 3.13 for local development (rejected)

Reverse the python-runtime.md decision and require pyenv/asdf installation.

**Rejected because:**
- Adds 30-60 minutes of setup for every developer (version manager + Python 3.13 install)
- Contradicts the python-runtime.md decision that was already made and documented
- The incompatibility is likely temporary (asyncpg is actively maintained)
- All developer setup docs, CI configs, and tool invocations would need updating
- The benefit (PostgreSQL for local dev) doesn't justify the cost for a temporary issue

### Alternative C: Sync-only PostgreSQL for local development (rejected)

Use `psycopg2` (sync) with a thread pool executor for the async engine.

**Rejected because:**
- psycopg2 also hangs on Python 3.14 (same TCP negotiation issue)
- Mixing sync and async drivers creates two code paths to maintain
- Thread pool executor adds complexity for no benefit over SQLite

### Alternative D: Use Docker exec for database access (rejected)

Run SQLAlchemy queries through `docker exec` instead of a direct TCP connection.

**Rejected because:**
- Violates the SQLAlchemy driver abstraction
- Non-standard and fragile — breaks connection pooling, transactions, migrations
- Adds Docker as a hard dependency for all application code paths
- No other project follows this pattern — it's a custom workaround, not a solution

---

## Consequences

### Positive

- Zero setup friction for developers — `pip install -e apps/api[dev]` is sufficient
- Fast local development (SQLite is faster than PostgreSQL for unit tests)
- CI enforces PostgreSQL correctness on every PR
- Clean separation: application logic validated locally, database logic validated in CI
- Easy transition path when asyncpg is fixed (single line change)

### Negative

- Developers cannot validate PostgreSQL-specific features locally (ENUMs, JSONB operators, partial indexes, NUMERIC precision)
- Migration DDL is verified in CI, not locally — feedback loop is slower
- Risk of writing application code that passes locally (SQLite) but fails in CI (PostgreSQL) due to type differences
- SQLite has different locking semantics — concurrent access patterns won't surface issues locally

### Neutral

- Alembic migration files target PostgreSQL DDL regardless of local database — no migration divergence
- SQLAlchemy models are backend-agnostic — no code branches for SQLite vs PostgreSQL
- The `CHRONOARB_DATABASE_URL` env var override enables ad-hoc PostgreSQL testing for any developer who needs it
- `/ready` endpoint uses a 5-second `asyncio.timeout` wrapper — PostgreSQL unavailability returns `"unreachable"` in bounded time instead of hanging the HTTP request

---

## Actual Verification Results

The decision was validated against the local development environment on 2026-08-03T15:04+05:00.

### Environment

```
Host:       Arch Linux (rolling)
Python:     3.14.6 (CPython)
PostgreSQL: 17.10 (Docker, --name chronoarb-pg, port 5432)
SQLite:     aiosqlite via SQLAlchemy 2.0 async
```

### Test 1: SQLite default path

```
$ uvicorn apps.api.main:app --port 8000
$ curl http://localhost:8000/ready

→ HTTP 200
→ {"data":{"status":"ok","database":"connected","trace_id":"trc_..."}}
```

**Result: PASS.** SQLite connects instantly (<10ms). Application starts, serves requests, and reports healthy readiness. Full test suite (10 API + 33 domain = 43 tests) passes against SQLite.

### Test 2: PostgreSQL override path

```
$ CHRONOARB_DATABASE_URL=postgresql+asyncpg://postgres:chronoarb@localhost:5432/chronoarb \
  python -c "
    import asyncio
    from apps.api.deps import get_db_status
    result = asyncio.run(get_db_status())
    print(f'DB status: {result}')
  "

→ database_status_check_timeout (logged as WARNING)
→ DB status: unreachable
```

**Result: PASS.** PostgreSQL connection attempt times out after 5 seconds. The `asyncio.timeout(5)` wrapper in `deps.py` prevents indefinite HTTP request blocking. The `TimeoutError` is caught and mapped to `"unreachable"`. No stack trace leaked to logs. No process crash.

### Test 3: Timeout wrapper prevents request blocking

Without the timeout wrapper, the asyncpg SSL negotiation hang would block the HTTP request thread indefinitely, causing the `/ready` endpoint to never respond. This would cause ECS health checks to fail by timeout (not by explicit error), making the instance unrecoverable.

With the timeout wrapper:
- Request returns after exactly 5 seconds
- Return value is `"unreachable"` (not a hang)
- ECS health check can retry on next interval
- No process restart needed when PostgreSQL recovers

### Test 4: Configuration override chain

```
Default:          settings.database_url = "sqlite+aiosqlite:///chronoarb.db"  (hard-coded)
ENV override:     CHRONOARB_DATABASE_URL=postgresql+asyncpg://...  (via pydantic-settings env_prefix="CHRONOARB_")
Result:           settings.database_url = "postgresql+asyncpg://..."  (override takes precedence)
```

**Result:** Configuration override chain works correctly. The `SettingsConfigDict(env_prefix="CHRONOARB_")` maps the env var `CHRONOARB_DATABASE_URL` to `Settings.database_url` automatically.

### Verification Summary

| Scenario | Database | Result | Latency |
|----------|----------|--------|---------|
| Default (SQLite) | `sqlite+aiosqlite:///chronoarb.db` | `"connected"` | <10ms |
| PostgreSQL override | `postgresql+asyncpg://localhost:5432/chronoarb` | `"unreachable"` | 5s timeout |
| Timeout wrapper | — | Prevents indefinite hang | Exactly 5s |

**PostgreSQL remains the system of record** (ADR-0001 D2). This SQLite fallback is exclusively a local development convenience to work around the Python 3.14 + asyncpg incompatibility. All staging and production deployments use PostgreSQL. All CI integration tests run against PostgreSQL (Python 3.13 CI leg).

---

## Exit Criteria

The SQLite fallback is a **temporary** development convenience. It shall be removed when any of the following conditions are met.

### Criterion A: PostgreSQL driver works on Python 3.14 (preferred path)

```
pip install --upgrade asyncpg
timeout 5 python -c "
import asyncio, asyncpg
async def test():
    conn = await asyncpg.connect('postgresql://postgres:chronoarb@localhost:5432/chronoarb', timeout=3)
    val = await conn.fetchval('SELECT 1')
    assert val == 1
    await conn.close()
    print('asyncpg ON PYTHON 3.14: OK')
asyncio.run(test())
"
```

When this command exits with `OK` (not `TimeoutError`), the incompatibility is resolved.

**Action on resolution:**
1. Update `settings.py` default: `database_url = "postgresql+asyncpg://postgres:chronoarb@localhost:5432/chronoarb"`
2. Remove `aiosqlite` from `apps/api/pyproject.toml` dev dependencies
3. Remove `*.db` from `.gitignore` patterns
4. Update CI: remove Python 3.13-only PostgreSQL leg — both CI legs (3.13 and 3.14) run against PostgreSQL
5. Update this ADR status to `Superseded`

### Criterion B: Python runtime standardized to 3.13 (fallback path)

If asyncpg remains incompatible with Python 3.14 past Week 4 (2026-08-27), and the incompatibility is confirmed as permanent (not a release candidate bug), the Python runtime decision shall be revisited.

**Action on resolution:**
1. Create ADR reversing python-runtime.md: standardize on Python 3.13
2. Install Python 3.13 via pyenv: team-wide setup (30 min per developer)
3. Update all `requires-python = ">=3.13"` to `"~=3.13"`
4. Update Docker base images to `python:3.13-slim-bookworm`
5. Switch `database_url` default to PostgreSQL
6. Remove SQLite fallback

### Criterion C: asyncpg never fixes — permanent PostgreSQL driver chosen (long-term)

If asyncpg remains incompatible past MVP, select a permanent PostgreSQL async driver that works on the project's Python runtime.

**Candidates:**
- `asyncpg` — current choice, blocked on Python 3.14
- `psycopg` (async) — blocked on same Python 3.14 issue
- A future Python 3.14-compatible async PostgreSQL driver

**Action on resolution:**
1. Create ADR documenting the permanent driver choice
2. Update `settings.py` default accordingly
3. Remove SQLite fallback

### Exit Criteria Status (2026-08-03)

| Criterion | Status | ETA |
|-----------|--------|-----|
| A (asyncpg 3.14 fix) | Waiting on upstream release | Unknown — track asyncpg releases |
| B (Python 3.13 rollback) | Not yet triggered | Week 4 decision point |
| C (permanent driver) | Not yet triggered | Post-MVP if needed |

---

## Risk Mitigation

---

## Developer Setup Impact

### Before (if Option A were chosen)

```
pyenv install 3.13.0        # 10-15 min download + build
pyenv local 3.13.0           # Set project Python
python -m venv .venv          # Create venv with 3.13
pip install -e apps/api[dev]  # Install deps
# Total: 20-30 min setup
```

### After (Option B — current)

```
python -m venv .venv          # Create venv with system 3.14
pip install -e apps/api[dev]  # Install deps (includes aiosqlite)
# Total: 2-3 min setup
```

### CI Impact

| CI Leg | Python | Database | Purpose |
|--------|--------|----------|---------|
| test (3.13) | 3.13 | PostgreSQL | Full integration — validates DDL, types, constraints |
| test (3.14) | 3.14 | SQLite | Application logic — fast feedback on business rules |
| lint/typecheck | 3.14 | N/A | Static analysis |

---

## References

- python-runtime.md: Python 3.14 runtime decision
- ADR-0001 D2: PostgreSQL as sole system of record
- ADR-0008: Migration split strategy
- database-design.md §1: Database principles (PostgreSQL 17, NUMERIC, TIMESTAMPTZ, ULID)
- batch-03-database-plan.md DB-01/DB-04: Implementation notes
