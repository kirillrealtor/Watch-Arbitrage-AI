# ChronoArb — Week 01 Execution Batches

**Plan type:** Batch-level execution sequencing
**Parent:** docs/implementation/week-01-plan.md
**Date:** 2026-08-03
**Status:** Ready

---

## Batch Overview

| Batch | Name | Tasks | Engineers Required | Estimated Duration |
|-------|------|-------|--------------------|--------------------|
| B1 | Repository foundation | 8 | 1 (DevOps) | 2.5 hours |
| B2 | Python + domain foundation | 9 | 2 (Backend #1 + Backend #2) | 3.0 hours |
| B3 | Database + backend skeleton | 7 | 1 (Backend #1) | 5.0 hours |
| B4 | Worker foundation | 2 | 1 (Backend #2) | 1.5 hours |
| B5 | Web + TypeScript foundation | 5 | 1 (Web) | 3.0 hours |
| B6 | Mobile foundation | 3 | 1 (Flutter) | 3.0 hours |
| B7 | Docker + infrastructure | 15 | 1 (DevOps) | 8.0 hours |
| B8 | CI pipeline + final verification | 6 | 1 (DevOps) | 4.0 hours |

**Complete 5-engineer parallel schedule:**

```
Day 1 AM:  B1 (DevOps) ─────────────────────────────────────────►
           B2 (Backend#1) ────────────────────►
           B2 (Backend#2) ────────────────────►

Day 1 PM:  B3 (Backend#1) ──────────────────────────────────────►
           B4 (Backend#2) ───────────►
           B5 (Web) ─────────────────────────►
           B6 (Flutter) ─────────────────────►

Day 2 AM:  B7a Docker (DevOps) ─────────►
           B3 cont. (Backend#1) ────────────► (finishes)

Day 2 PM:  B7b Infra (DevOps) ───────────────────────────────────►
           B8 CI (DevOps) ──────────────────────────►
```

---

## Batch 1: Repository Foundation

### Objective
Create every root-level configuration file. After this batch, `pnpm install` succeeds and the workspace topology is visible. All tooling configs exist but enforce nothing yet (no code to lint).

### Included Tasks

| TaskID | Description | Size | Deps |
|--------|-------------|------|------|
| WF-07 | Create `.gitignore` and `.dockerignore` | XS | None |
| WF-01 | Initialize root `package.json` with workspace scripts | XS | None |
| WF-02 | Create `pnpm-workspace.yaml` | XS | WF-01 |
| WF-04 | Create root `tsconfig.base.json` | XS | WF-01 |
| WF-05 | Create root `pyproject.toml` with tool configs | XS | WF-01 |
| WF-03 | Create `turbo.json` with pipeline stages | Small | WF-02 |
| WF-06 | Create `.importlinter` | XS | WF-05, ADR-0007 |
| WF-08 | Create `AGENTS.md` at module roots | XS | Root AGENTS.md |

### Dependencies
- None. This is the first batch. All tasks except WF-07 and WF-01 are independent of each other once WF-01 completes (they only depend on the file existing, not its contents being finalized).
- WF-02 must come after WF-01 (references workspace names in package.json).
- WF-03 must come after WF-02 (references workspace names in pnpm-workspace.yaml).
- WF-06 requires knowledge of ADR-0007 dependency graph (read-only — no code depends on it yet).

### Parallel Work Allowed
All XS tasks can execute in parallel after WF-01 completes. WF-03 is the only sequential task (Small, ~45 min) and can run in the second half of the batch window.

### Risks
- **pnpm version mismatch:** Different engineers may have different pnpm versions. Pin `packageManager` field in root `package.json` to `pnpm@9.x`.
- **TypeScript path aliases in WF-04:** If `@chronoarb/*` aliases don't match actual package names, later batches will break. Verify against `pnpm-workspace.yaml` package names.

### Verification Gates
```bash
git status                                 # Only new config files, no generated content
node --version && pnpm --version           # Confirmed versions
pnpm install                               # Installs with zero packages (empty workspace)
cat pnpm-workspace.yaml                    # Lists apps/* and packages/*
pnpm turbo run build --dry-run             # Pipeline graph renders without errors
tsc --showConfig --project tsconfig.base.json  # Strict mode confirmed
ruff check .                               # "No Python files found" (not an error)
mypy --version                             # Installed and accessible
cat .importlinter                          # Layers and forbidden rules present
```

### Expected Repository State After Completion
```
chronoarb/
├── package.json          # pnpm workspace root, scripts defined
├── pnpm-workspace.yaml   # apps/*, packages/*
├── turbo.json            # build/lint/test/typecheck pipelines
├── tsconfig.base.json    # Strict, ES2022, @chronoarb/* aliases
├── pyproject.toml        # ruff, mypy, pytest, coverage configs
├── .importlinter         # ADR-0007 dependency enforcement
├── .gitignore            # Excludes node_modules, __pycache__, .env*, .terraform, dist/
├── .dockerignore         # Excludes build artifacts
├── apps/api/AGENTS.md    # Module-specific engineering rules
├── packages/domain-python/AGENTS.md  # Module-specific engineering rules
└── pnpm-lock.yaml        # Empty lockfile
```

---

## Batch 2: Python + Domain Foundation

### Objective
Create all Python package configurations and the domain-layer value objects. After this batch, all five Python packages install with editable dependencies, the `Money` value object and `SourceAdapter` Protocol are importable, and the import-linter contract validates the package boundary graph.

### Included Tasks

| TaskID | Description | Size | Deps |
|--------|-------------|------|------|
| WF-09 | Create `packages/domain-python/pyproject.toml` | XS | WF-05 (B1) |
| WF-13 | Create `domain-python/chronoarb/domain/` package skeleton | XS | WF-09 |
| WF-10 | Create `packages/source-adapters/pyproject.toml` | XS | WF-09, ADR-0007 |
| WF-11 | Create `apps/api/pyproject.toml` | XS | WF-09 |
| WF-12 | Create `apps/worker/pyproject.toml` | XS | WF-09, WF-10 |
| WF-20 | Write `chronoarb/domain/ulid.py` — ULID generator | XS | WF-13 |
| WF-48 | Write `test_money.py` | XS | WF-13 |
| WF-49 | Write `test_ulid.py` | XS | WF-20 |
| WF-50 | Write import-linter contract test | XS | WF-06 (B1), ADR-0007 |

### Dependencies
- WF-09 must complete first (other pyproject.toml files reference it as a dependency).
- WF-13 must complete before WF-20 (ULID lives in the same package structure).
- WF-10 references `chronoarb-domain` as a dependency — ensure WF-09 is installed before WF-10.
- WF-48/49 depend on the code they test existing and importing correctly.

### Parallel Work Allowed
WF-10, WF-11, and WF-12 can run in parallel once WF-09 completes (all three create pyproject.toml files independently). WF-13 can run immediately after WF-09 (it creates files in the package WF-09 defines). WF-20, WF-48, WF-49, and WF-50 can all run in parallel once WF-13 and WF-20 complete.

**Parallel split:**
- Engineer A: WF-09 → WF-13 → WF-20 → WF-48, WF-49 (domain focus)
- Engineer B: WF-10, WF-11, WF-12 in parallel after WF-09 (package configs)

### Risks
- **pip editable install:** `pip install -e packages/domain-python` may fail if pyproject.toml has invalid TOML syntax. Verify syntax before installing.
- **Protocol runtime_checkable:** `@runtime_checkable` is only available in Python 3.8+. Confirmed available in 3.13.
- **Decimal import in Money:** `from decimal import Decimal` is stdlib but if any engineer accidentally types `from decimal import Decimal as D`, mypy will catch the inconsistency later.
- **import-linter false pass:** With only Protocol defined and no adapter implementations, import-linter has nothing to flag. This is expected — the contract exists, violations will be caught when adapters are added in Week 3.

### Verification Gates
```bash
pip install -e packages/domain-python                               # Installs chronoarb-domain
pip install -e packages/source-adapters                             # Installs chronoarb-adapters (depends on domain)
pip install -e apps/api                                             # Installs FastAPI + SQLAlchemy + Alembic
pip install -e apps/worker                                          # Installs worker with aioboto3
python -c "from chronoarb.domain.money import Money; m = Money(100, 'USD'); print(m)"  # Money works
python -c "from chronoarb.domain.source_adapters.protocol import SourceAdapter; print(SourceAdapter)"  # Protocol importable
python -c "from chronoarb.domain.ulid import generate_ulid; assert generate_ulid('org').startswith('org_')"  # ULID works
pytest packages/domain-python/tests/ -v                             # test_money + test_ulid pass
import-linter                                                       # No forbidden imports detected
```

### Expected Repository State After Completion
```
packages/domain-python/
├── pyproject.toml              # chronoarb-domain, Python >=3.13
├── chronoarb/domain/
│   ├── __init__.py
│   ├── money.py                # Money(amount: Decimal, currency: str)
│   ├── ulid.py                 # generate_ulid(prefix) → "org_01J..."
│   ├── errors.py               # DomainError, ValidationError, CurrencyMismatchError
│   └── source_adapters/
│       ├── __init__.py
│       └── protocol.py         # SourceAdapter Protocol (5 methods per ADR-0007)
└── tests/
    ├── test_money.py           # Creation, arithmetic, precision, mismatch
    └── test_ulid.py            # Prefix, uniqueness, sortability

packages/source-adapters/
├── pyproject.toml              # Depends on chronoarb-domain
└── chronoarb/adapters/
    └── __init__.py             # Empty placeholder

apps/api/
└── pyproject.toml              # fastapi, uvicorn, sqlalchemy[asyncio], alembic, pydantic, asyncpg

apps/worker/
└── pyproject.toml              # Depends on chronoarb-domain + chronoarb-adapters; aioboto3
```

---

## Batch 3: Database + Backend Skeleton

### Objective
Create the Alembic migration framework, write the initial migration for all 22 tables incorporating ADR-0002/0004/0005 corrections, build the FastAPI application shell with health endpoints, create all 12 backend module directories, and wire up the async SQLAlchemy engine. After this batch, `alembic upgrade head` creates a complete database and `uvicorn` serves a health-checking API.

### Included Tasks

| TaskID | Description | Size | Deps |
|--------|-------------|------|------|
| WF-18 | Create Alembic configuration | Small | WF-11 (B2) |
| WF-19 | Write initial migration (all 22 tables) | Medium | WF-18, database-design.md, ADR-0002, ADR-0004, ADR-0005 |
| WF-21 | Create FastAPI application shell | Small | WF-11 (B2), WF-13 (B2) |
| WF-22 | Create 12 backend module directories | XS | WF-21 |
| WF-23 | Create SQLAlchemy async engine and session factory | XS | WF-21 |
| WF-47 | Write `test_health.py` | XS | WF-21 |
| — | Create PostgreSQL database (Docker) | — | Docker (or local) |

**Note:** WF-19 is the single largest task in Week 1 (~2-3 hours). It requires careful transcription of all 22 table definitions from `database-design.md` with the ADR-mandated corrections. This task must be done by the most senior backend engineer with the database design document open side-by-side.

### Dependencies
- WF-18 needs Alembic installed (from WF-11 in B2). It also needs PostgreSQL running locally — this can be a local install or the Docker container started from B7 (Docker). For this batch, start PostgreSQL directly: `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=chronoarb postgres:18`.
- WF-19 depends on WF-18 (needs `alembic.ini` and `env.py` to exist).
- WF-21 depends on FastAPI + Pydantic installed (from WF-11 in B2) and domain types (from WF-13 in B2).
- WF-22 and WF-23 are independent of each other once WF-21 exists.
- WF-47 depends on WF-21 (needs the app object to test).

### Parallel Work Allowed
WF-18 and WF-21 can run in parallel (they use different parts of the `apps/api/` directory). WF-22, WF-23, and WF-47 can all run in parallel once WF-21 completes. WF-19 is a solo task — it must run after WF-18 and requires full focus.

**Sequential flow:**
1. Start PostgreSQL Docker container (30 seconds)
2. WF-18 + WF-21 in parallel (1 hour combined)
3. WF-19 (2-3 hours, solo)
4. WF-22 + WF-23 + WF-47 in parallel (30 minutes combined)

### Risks
- **PostgreSQL 18 Docker image:** Confirm `postgres:18` tag exists before starting. If not available, use `postgres:17` and document the version delta.
- **Migration downgrade:** Alembic downgrade may not work for all DDL if `ALTER TABLE` operations in the migration don't have explicit downgrade paths. Test `alembic downgrade -1` immediately after `alembic upgrade head`.
- **ADR-0002 UNIQUE constraint:** Must explicitly NOT include the composite UNIQUE on `alert_deliveries`. Double-check the migration SQL before running.
- **ADR-0004 observation_at NOT NULL:** This column has no default — it must be populated at normalization time during Week 6-8. For Week 1, the migration creates the column successfully because the table is empty at creation.
- **ADR-0005 fx_source NOT NULL:** Same concern — no rows exist at migration time, so the constraint passes. In Week 6-8, the normalization worker must always populate this field.

### Verification Gates
```bash
docker run -d --name chronoarb-pg -p 5432:5432 -e POSTGRES_PASSWORD=chronoarb postgres:18
export DATABASE_URL=postgresql+asyncpg://postgres:chronoarb@localhost:5432/chronoarb
createdb chronoarb                                                         # Create database
alembic upgrade head                                                       # Creates all 22 tables
psql -d chronoarb -c "\dt"                                                # List all 22 tables
psql -d chronoarb -c "\d alert_deliveries"                                # Verify org_id + material_version columns exist
psql -d chronoarb -c "\d normalized_listings"                             # Verify observation_at, fx_source, fx_date
alembic downgrade -1                                                       # Reverses cleanly
alembic upgrade head                                                       # Re-creates cleanly
uvicorn apps.api.main:app --port 8000 &                                   # Start API
curl http://localhost:8000/health                                          # {"status":"ok","trace_id":"..."}
curl http://localhost:8000/health/ready                                    # Check DB connectivity
kill %1                                                                   # Stop API
pytest apps/api/tests/test_health.py -v                                   # Health tests pass
find apps/api -type d | grep -E "(domain|application|infrastructure|api)$" | wc -l  # 48 directories
```

### Expected Repository State After Completion
```
alembic/
├── alembic.ini                           # Async SQLAlchemy, reads DATABASE_URL
├── env.py                                # Async engine, migration context
├── script.py.mako                        # Migration template
└── versions/
    └── 001_initial_schema.py             # Up/down for all 22 tables

apps/api/
├── pyproject.toml                        # (from B2)
├── apps/api/
│   ├── main.py                           # FastAPI app, /health, /health/ready, lifespan
│   ├── deps.py                           # get_db dependency
│   └── middleware/
│       ├── tracing.py                    # trace_id injection + logging
│       └── error_handler.py              # Pydantic error → API error envelope
├── tests/
│   └── test_health.py                    # Tests /health and /health/ready
└── <12 module directories>/              # identity, catalog, sources, listings,
    └── domain/, application/,            # normalization, duplicates, valuation,
        infrastructure/, api/             # opportunities, alerts, feedback,
                                          # billing, operations
apps/api/infrastructure/
└── database.py                           # AsyncEngine, async_sessionmaker, get_db
```

---

## Batch 4: Worker Foundation

### Objective
Create the worker process entry point, SQS client skeleton, OpenTelemetry tracing skeleton, and worker type registry. After this batch, `WORKER_TYPE=discovery python -m apps.worker.main` starts a process that connects to a queue stub (no real SQS) and logs "Worker X started".

### Included Tasks

| TaskID | Description | Size | Deps |
|--------|-------------|------|------|
| WF-24 | Create worker entry point | Small | WF-12 (B2), WF-23 (B3) |
| WF-25 | Create worker type registry | XS | WF-24 |

### Dependencies
- WF-24 needs `aioboto3` installed (from WF-12 in B2), `apps.api.infrastructure.database` importable (from WF-23 in B3), and `chronoarb.domain` importable (from B2).
- WF-25 is a pure function mapping strings to handlers — it depends on WF-24 only for the handler type definition.

### Parallel Work Allowed
WF-25 can start once WF-24's handler type is defined (~15 minutes into WF-24). These two tasks are closely coupled — same engineer should do both sequentially.

### Risks
- **SQS stub vs real SQS:** The worker might try to connect to AWS SQS if `AWS_ENDPOINT_URL` is not set. The skeleton should check for the env var and use LocalStack endpoint when present, or log a warning and skip SQS operations when absent.
- **WORKER_TYPE for unknown types:** Must exit with code 1 (not hang or crash silently). Regression test: `WORKER_TYPE=invalid python -m apps.worker.main; echo $?` → 1.
- **OpenTelemetry skeleton without exporter:** The tracing module should be a no-op when no exporter is configured. Don't crash the worker if OTLP endpoint is unreachable.

### Verification Gates
```bash
export DATABASE_URL=postgresql+asyncpg://postgres:chronoarb@localhost:5432/chronoarb
WORKER_TYPE=discovery python -m apps.worker.main 2>&1 | head -5                # "Worker discovery started"
WORKER_TYPE=invalid python -m apps.worker.main; echo $?                         # Exit code 1
python -c "from apps.worker.shared.sqs_client import SqsClient; print(SqsClient)"  # Importable
python -c "from apps.worker.shared.tracing import setup_tracing; setup_tracing()"   # No-op when no exporter
```

### Expected Repository State After Completion
```
apps/worker/
├── pyproject.toml                        # (from B2)
├── apps/worker/
│   ├── main.py                           # Entry point, WORKER_TYPE env var, event loop
│   ├── registry.py                       # WORKER_TYPE → handler function mapping
│   └── shared/
│       ├── sqs_client.py                 # SQS receive/delete/dlq skeleton
│       └── tracing.py                    # OpenTelemetry no-op skeleton
```

---

## Batch 5: Web + TypeScript Foundation

### Objective
Create TypeScript workspace packages, Next.js application shell with Tailwind CSS, and placeholder page. After this batch, `pnpm dev` in `apps/web` serves a blank page at localhost:3000 with Tailwind classes compiling.

### Included Tasks

| TaskID | Description | Size | Deps |
|--------|-------------|------|------|
| WF-14 | Create `apps/web/package.json` | XS | WF-04 (B1) |
| WF-15 | Create `apps/web/tsconfig.json` | XS | WF-04 (B1), WF-14 |
| WF-16 | Create `packages/design-tokens/package.json` | XS | None |
| WF-17 | Create `packages/api-client-ts/package.json` | XS | None |
| WF-26 | Create Next.js app shell | Small | WF-14, WF-15 |

### Dependencies
- WF-14 and WF-15 need `tsconfig.base.json` from B1 for the `extends` field.
- WF-16 and WF-17 have no dependencies — they're standalone package.json files for empty packages.
- WF-26 needs Next.js and Tailwind installed (from WF-14) and tsconfig (from WF-15).

### Parallel Work Allowed
WF-14, WF-15, WF-16, and WF-17 can all be created in parallel (they're independent config files in different directories). WF-26 runs after WF-14 and WF-15 complete.

**Parallel split:**
- Minutes 1-30: All XS tasks in parallel
- Minutes 30-90: WF-26 (Next.js app shell)

### Risks
- **Next.js 16.2 not released:** The SRS specifies 16.2.x but as of August 2026, Next.js 16 may not be at 16.2 yet. Install `next@latest` (16.x) and document the exact version installed. Create a version tracking note.
- **Tailwind v4 vs v3:** Tailwind CSS v4 changed the configuration format. Verify which major version is current and use the corresponding config format. The `tailwind.config.ts` in the plan assumes v3-style config. If v4, use CSS-based config instead.
- **pnpm workspace dependency:** Next.js needs React and React DOM as peer dependencies. Ensure `pnpm install` resolves them correctly in the workspace context.

### Verification Gates
```bash
pnpm install --filter @chronoarb/web                                    # Installs Next.js + deps
pnpm --filter @chronoarb/web exec tsc --noEmit                          # Zero TypeScript errors
pnpm --filter @chronoarb/web dev &                                      # Start dev server
sleep 5
curl -s http://localhost:3000 | head -20                                # HTML page loads
kill %1
pnpm --filter @chronoarb/web build                                      # Production build succeeds
pnpm install --filter @chronoarb/design-tokens                          # Design tokens package resolves
pnpm install --filter @chronoarb/api-client                             # API client package resolves
```

### Expected Repository State After Completion
```
apps/web/
├── package.json                    # next@16.2, react@19, tailwind, tanstack-query, react-hook-form, zod
├── tsconfig.json                   # Extends root, includes app/components/hooks/lib
├── next.config.ts                  # Minimal config
├── tailwind.config.ts              # Content paths, theme extensions
├── postcss.config.js               # Tailwind + autoprefixer
├── app/
│   ├── layout.tsx                  # Root layout: html, body, metadata
│   └── page.tsx                    # Blank placeholder: "ChronoArb — Ready"
└── lib/
    └── api/                        # Empty; awaiting generated client (Week 3)

packages/design-tokens/
├── package.json                    # @chronoarb/design-tokens
└── tokens/
    └── colors.ts                   # Placeholder palette

packages/api-client-ts/
├── package.json                    # @chronoarb/api-client
└── src/
    └── index.ts                    # Empty export
```

---

## Batch 6: Mobile Foundation

### Objective
Create the Flutter application shell with all required dependencies, feature directory structure, and a passing widget test. After this batch, `flutter build apk --debug` succeeds and `flutter test` passes.

### Included Tasks

| TaskID | Description | Size | Deps |
|--------|-------------|------|------|
| WF-27 | Create Flutter app shell | Small | None |
| WF-28 | Create Flutter feature directory skeleton | XS | WF-27 |
| WF-51 | Write widget test for Flutter placeholder | XS | WF-27 |

### Dependencies
- WF-27 has no dependencies on other batches. Flutter toolchain is independent of pnpm, Python, and Docker. The Flutter engineer can start immediately.
- WF-28 and WF-51 depend on WF-27 (need the app directory to exist).
- The `api-client-dart` package (`packages/api-client-dart/pubspec.yaml`) was not listed as a Week 1 task in the plan. It's a placeholder for generated code (Week 3). Create it as part of WF-27's directory scaffolding.

### Parallel Work Allowed
WF-28 and WF-51 can run in parallel once WF-27 completes (they touch different subdirectories of `apps/mobile/`). This batch is a solo task for the Flutter engineer — no other batch depends on it.

### Risks
- **Flutter 3.44 not released:** This is the highest-likelihood risk in Week 1. The SRS specifies 3.44.x but Flutter releases are not predictable. Install the latest stable 3.x release available. Document the actual version. If version mismatch with SRS is significant (e.g., 3.27 vs 3.44), create a brief version-tracking note for the Week 1 closeout.
- **Riverpod 3.x API changes:** Riverpod v3 introduced code generation via `riverpod_annotation`. Confirm the current stable version and use its API. If code generation is required, include `build_runner` in dev dependencies.
- **Dart SDK compatibility:** Ensure the Dart SDK version in `pubspec.yaml` matches the Flutter SDK's bundled Dart version.

### Verification Gates
```bash
cd apps/mobile
flutter doctor                                                               # Verify toolchain
flutter pub get                                                              # Resolve all dependencies
flutter analyze                                                              # Zero Dart analysis issues
flutter test                                                                 # Widget test passes
flutter build apk --debug                                                    # APK builds successfully
find lib -type d | sort                                                      # All feature directories present
cd ../..
cat packages/api-client-dart/pubspec.yaml                                    # Placeholder exists
```

### Expected Repository State After Completion
```
apps/mobile/
├── pubspec.yaml                      # flutter, riverpod, go_router, dio, freezed, drift
├── lib/
│   ├── main.dart                     # MaterialApp with placeholder home
│   ├── app/
│   │   ├── bootstrap.dart            # App initialization stub
│   │   ├── router.dart               # go_router placeholder
│   │   └── theme.dart                # Basic ThemeData with design tokens placeholder
│   ├── core/
│   │   ├── api/                      # Empty; awaiting generated client
│   │   ├── auth/                     # Empty
│   │   ├── storage/                  # Empty
│   │   ├── notifications/            # Empty
│   │   └── telemetry/                # Empty
│   └── features/
│       ├── onboarding/               # Empty
│       ├── opportunities/            # presentation/, application/, domain/, data/
│       ├── watches/                  # Empty
│       ├── alerts/                   # Empty
│       ├── activity/                 # Empty
│       └── settings/                 # Empty
└── test/
    └── widget_test.dart              # Default counter test passes

packages/api-client-dart/
├── pubspec.yaml                      # @chronoarb/api_client
└── lib/
    └── api_client.dart               # Empty export
```

---

## Batch 7: Docker + Infrastructure

### Objective
Create Dockerfiles for API and worker, Docker Compose for local development, and complete Terraform module set for all AWS resources. After this batch, `docker compose up` runs a full local stack and `terraform plan` produces a clean plan output for the staging environment.

### Included Tasks

| TaskID | Description | Size | Deps |
|--------|-------------|------|------|
| **Docker subset** ||||
| WF-29 | Create `Dockerfile.api` | Small | WF-11 (B2), WF-21 (B3) |
| WF-30 | Create `Dockerfile.worker` | XS | WF-12 (B2), WF-24 (B4) |
| WF-31 | Create `docker/compose.yaml` | Small | WF-29, WF-30, WF-19 (B3) |
| WF-32 | Create `.env.example` | XS | WF-31 |
| **Infrastructure subset** ||||
| WF-33 | Create Terraform root module | Small | None |
| WF-34 | Create VPC module | Medium | WF-33 |
| WF-35 | Create RDS module | Small | WF-34 |
| WF-36 | Create ElastiCache module | Small | WF-34 |
| WF-37 | Create S3 module | XS | WF-33 |
| WF-38 | Create ECR module | XS | WF-33 |
| WF-39 | Create ECS module | Small | WF-34, WF-35, WF-38 |
| WF-40 | Create SQS module | Small | WF-34 |
| WF-41 | Create Cognito module | Small | WF-33 |
| WF-42 | Create IAM module | Small | WF-34, WF-35, WF-36, WF-37, WF-38, WF-39, WF-40, WF-41 |
| WF-43 | Create environment tfvars | XS | WF-33 |

### Dependencies

**Docker subset chain:**
- WF-29, WF-30: Need the `pyproject.toml` from B2 and the app skeletons from B3/B4 to know what to COPY and what CMD to use.
- WF-31: Needs all Dockerfiles to exist and the migration from B3 to know the database schema.
- WF-32: References env vars from WF-31's service definitions.

**Infrastructure subset chain:**
- WF-33: Terraform root module with providers, backend, variables. No upstream dependencies.
- WF-34: VPC — depends on WF-33 for provider/region config.
- WF-35, WF-36, WF-40: Depend on WF-34 (need subnet IDs).
- WF-37, WF-38, WF-41: Depend on WF-33 only (standalone resources).
- WF-39: Depends on WF-34 (subnets), WF-35 (RDS endpoint), WF-38 (ECR repo ARNs).
- WF-42: Depends on all infrastructure modules (needs ARNs from all resources).
- WF-43: Depends on WF-33 (needs variable definitions).

### Parallel Work Allowed

This batch has two independent tracks that can run in parallel:
- **Docker track:** WF-29 → WF-30 (parallel) → WF-31 → WF-32
- **Infrastructure track:** WF-33 → parallel group {WF-34, WF-37, WF-38, WF-41} → parallel group {WF-35, WF-36, WF-39, WF-40} after WF-34 → WF-42 → WF-43

The tracks are fully independent of each other. If only one DevOps engineer is available, do Docker first (shorter, ~2 hours) then Infrastructure (~6 hours).

**Infrastructure parallelization detail:**
- After WF-33, launch 4 modules in parallel: WF-37 (S3), WF-38 (ECR), WF-41 (Cognito) — these only need the root module
- WF-34 (VPC) is the blocking dependency for most everything else — start it first
- After WF-34 completes, launch 5 modules in parallel: WF-35 (RDS), WF-36 (ElastiCache), WF-39 (ECS), WF-40 (SQS)
- WF-42 (IAM) is the final infrastructure task — it needs ARNs from all 8 modules
- WF-43 (tfvars) can be done independently

### Risks
- **Python 3.13 Docker image:** Verify `python:3.13-slim-bookworm` exists. If not, use `python:3.13-slim` or `python:3.12-slim-bookworm` and document.
- **LocalStack SQS emulation:** LocalStack Community edition may not support all SQS features. Verify that basic send/receive/delete works. If not, fall back to ElasticMQ for local SQS simulation.
- **Terraform AWS provider version:** Pin to `>= 5.0, < 6.0` to avoid unexpected breaking changes.
- **NAT Gateway cost:** VPC with NAT Gateway costs ~$32/month even when idle. For staging, consider using VPC endpoints for S3/DynamoDB/SQS to avoid NAT Gateway. Document this cost trade-off.
- **PostgreSQL 18 in AWS RDS:** Verify RDS supports PostgreSQL 18. If not, use 17.x and document the delta. The migration should work identically on both versions.
- **S3 backend for Terraform state:** The `terraform.tf` backend config references an S3 bucket that doesn't exist yet. For Week 1, use local state. Document the S3 backend config but comment it out until the bucket is created.

### Verification Gates

**Docker:**
```bash
docker build -f docker/Dockerfile.api -t chronoarb-api .
docker build -f docker/Dockerfile.worker -t chronoarb-worker .
docker compose -f docker/compose.yaml up -d                          # All services start
docker compose -f docker/compose.yaml ps                              # All services healthy
docker compose -f docker/compose.yaml exec api curl -s localhost:8000/health  # 200
docker compose -f docker/compose.yaml exec api alembic upgrade head   # Schema created
docker compose -f docker/compose.yaml down -v                         # Clean shutdown
```

**Infrastructure:**
```bash
cd infrastructure/terraform
terraform init                                                        # Provider plugins downloaded
terraform validate                                                    # No config errors
terraform fmt -check -recursive                                       # All files formatted
terraform plan -var-file=environments/staging.tfvars                  # Clean plan, no errors
terraform plan -var-file=environments/production.tfvars               # Clean plan, no errors
cd ../..
```

### Expected Repository State After Completion
```
docker/
├── Dockerfile.api                    # Multi-stage: build → uvicorn, Python 3.13-slim
├── Dockerfile.worker                 # Same base, WORKER_TYPE override
├── compose.yaml                      # postgres, redis, localstack, api, worker
└── .env.example                      # All required env vars with placeholder values

infrastructure/terraform/
├── main.tf                           # AWS provider, S3 backend (commented), region
├── terraform.tf                      # Required version constraints
├── variables.tf                      # Environment, region, instance sizes
├── outputs.tf                        # RDS endpoint, ALB DNS, ECR URLs, Cognito pool ID
├── vpc.tf                            # 2 AZs, public/private subnets, NAT GW, flow logs
├── rds.tf                            # PostgreSQL 18, encrypted, automated backups
├── elasticache.tf                    # Redis 7/Valkey, small node, VPC-only
├── s3.tf                             # Evidence bucket (KMS, versioned), artifact bucket
├── ecr.tf                            # api + worker repos, scan on push, lifecycle 10
├── ecs.tf                            # Fargate cluster, task defs, ALB, service
├── sqs.tf                            # 7 queues + 7 DLQs, redrive policy, 4-day retention
├── cognito.tf                        # User pool, app client (auth code + PKCE), domain
├── iam.tf                            # ECS task roles, CI deploy role
└── environments/
    ├── staging.tfvars                # Small instances, soft delete
    └── production.tfvars             # Backed-up, MFA-delete
```

---

## Batch 8: CI Pipeline + Final Verification

### Objective
Create the GitHub Actions CI workflow, CI helper scripts, and run the complete Week 1 verification checklist. After this batch, a push to `main` triggers a green CI pipeline covering lint, type-check, test, build, import-linter, and Terraform validation.

### Included Tasks

| TaskID | Description | Size | Deps |
|--------|-------------|------|------|
| WF-44 | Create CI workflow | Medium | WF-01 through WF-43 (all prior batches) |
| WF-45 | Create `scripts/ci-lint.sh` | XS | WF-05 (B1) |
| WF-46 | Create `scripts/ci-test.sh` | XS | WF-05 (B1) |
| — | Run full Week 1 verification checklist | — | All batches complete |
| — | Fix any failures discovered by CI | — | WF-44 |
| — | Commit and push to trigger first green CI run | — | All prior |

### Dependencies
- WF-44 needs every prior batch complete. The CI workflow references tool paths, test commands, and build scripts that don't exist until all infrastructure is in place.
- WF-45 and WF-46 are simple shell scripts that reference `ruff`, `mypy`, and `pytest`. They can be created early (they don't depend on code existing) but only become meaningful when all code is written.
- The verification checklist MUST pass completely before marking this batch complete.

### Parallel Work Allowed
WF-45 and WF-46 are independent and can be created in parallel. WF-44 is a solo task (~2-3 hours) that requires understanding every tool and command across the entire repository. The verification checklist and CI fix iterations are sequential — run the checklist, fix failures, re-run.

### Risks
- **CI runner Python version:** GitHub Actions `ubuntu-latest` may not have Python 3.13 by default. Use `setup-python@v5` with `python-version: '3.13'`.
- **pnpm cache in CI:** Without caching, `pnpm install` can take several minutes. Configure `actions/setup-node` with pnpm and enable caching.
- **Terraform in CI:** `terraform validate` requires `terraform init` which needs AWS credentials (even for validation). Configure AWS credentials as GitHub Secrets or use `--backend=false` for validate-only runs.
- **First CI run may not be green:** Expect 2-3 iterations of fixing issues (missing files, incorrect paths, version mismatches). Budget 1 hour for fix iterations after the initial WF-44 commit.
- **import-linter in CI:** May fail if any package accidentally imports from a forbidden layer. Fix violations before merging.

### Verification Gates

Run the complete checklist from week-01-plan.md §10:

```bash
# === Build & Install ===
pnpm install --frozen-lockfile                     # All workspaces resolve
pnpm turbo run build                               # All packages build

# === Lint ===
ruff check .                                        # Zero Python lint errors
pnpm turbo run lint                                 # Zero TS lint errors
terraform fmt -check -recursive infrastructure/terraform/  # Terraform formatted

# === Type Check ===
mypy packages/domain-python/                        # Zero type errors
mypy apps/api/                                      # Zero type errors
mypy apps/worker/                                   # Zero type errors
pnpm --filter @chronoarb/web exec tsc --noEmit      # Zero TS errors

# === Test ===
pytest apps/api/ apps/worker/ packages/ -v          # All tests pass
pnpm --filter @chronoarb/web exec vitest run        # Web tests pass
cd apps/mobile && flutter test && cd ../..          # Flutter test passes
import-linter                                        # No forbidden imports

# === Database ===
docker compose -f docker/compose.yaml up -d postgres
alembic upgrade head                                # All 22 tables created
alembic downgrade -1                                # Reverses cleanly
alembic upgrade head                                # Re-creates cleanly

# === Runtime ===
uvicorn apps.api.main:app --port 8000 &
curl -s http://localhost:8000/health | python -m json.tool    # {"status":"ok"}
kill %1

WORKER_TYPE=discovery python -m apps.worker.main 2>&1 | head -3   # Started

# === Infrastructure ===
cd infrastructure/terraform
terraform init && terraform validate
terraform plan -var-file=environments/staging.tfvars 2>&1 | tail -5  # No errors
cd ../..

# === Docker ===
docker compose -f docker/compose.yaml up -d
docker compose -f docker/compose.yaml exec api curl -s localhost:8000/health
docker compose -f docker/compose.yaml down -v

# === CI ===
gh workflow run ci.yml
gh run watch                                         # Wait for green
```

### Expected Repository State After Completion

The full repository matches the tree in week-01-plan.md §3. Every file in the expected deliverables list exists and passes its verification gate. CI is green on `main`.

---

## Batch Execution Summary

| Order | Batch | Blocking for | Earliest start |
|-------|-------|-------------|----------------|
| 1 | B1: Repository foundation | B2, B3, B5, B7 | Immediately |
| 2 | B2: Python + domain | B3, B4, B7 | After B1 (WF-01/05) |
| 3 | B5: Web + TypeScript | B8 | After B1 (WF-01/04) |
| 3 | B6: Mobile | B8 | Immediately (no deps) |
| 4 | B3: Database + backend | B4, B7 | After B2 |
| 5 | B4: Worker foundation | B7 | After B2 + B3 |
| 6 | B7: Docker + infra | B8 | After B2, B3, B4 |
| 7 | B8: CI + verification | — | After all batches |

**Legend:** Batches at the same "order" level can run in parallel. B5 and B6 are independent of B2 and can start as early as B1 completes. B7 can start Docker work early (after B2) but infrastructure work waits for B3/B4 for accurate service definitions.

---

## Batch Dependency Graph

```
B1 (Repository)
│
├──► B2 (Python + Domain) ──► B3 (Database + Backend) ──► B4 (Worker)
│                                  │                          │
├──► B5 (Web + TypeScript) ────────┤                          │
│                                  │                          │
└──► B6 (Mobile) ─────────────────┤                          │
                                  │                          │
                                  ▼                          ▼
                              B7 (Docker + Infrastructure)
                                  │
                                  ▼
                              B8 (CI + Verification)
```
