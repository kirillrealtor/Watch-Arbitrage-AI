# ChronoArb — Week 01 Implementation Plan

**Plan type:** Sprint execution plan
**Dates:** Week 1 of 16 (Architecture Baseline)
**Status:** Ready
**Based on:** development-roadmap.md §4 (Weeks 1-2), all 7 ADRs, architecture-review.md

---

## 1. Week 1 Objective

Establish every runtime, toolchain, and infrastructure artifact needed so that **Week 2 begins with `pnpm dev` and `docker compose up` working for every engineer on the team**. No business logic or features are implemented. The deliverable is a green CI pipeline and a local development environment that passes all foundation tests.

---

## 2. Implementation Goals

| # | Goal | Measurable Outcome |
|---|------|-------------------|
| G1 | Monorepo bootable | `pnpm install` succeeds across all workspaces |
| G2 | CI pipeline green | Lint, type-check, and test pass on `main` in GitHub Actions |
| G3 | Database migratable | `alembic upgrade head` creates all 22 tables locally |
| G4 | API server starts | `uvicorn apps.api.main:app` returns 200 on `/health` |
| G5 | Worker starts | Worker process connects to queue stub and logs ready |
| G6 | Web dev server starts | `pnpm dev` in `apps/web` serves a blank page |
| G7 | Mobile compiles | `flutter build` succeeds for stub app |
| G8 | Docker Compose works | `docker compose up` runs PostgreSQL + Redis + LocalStack |
| G9 | Terraform plan clean | `terraform plan` in staging workspace shows no errors |
| G10 | Import boundaries enforced | `import-linter` passes with ADR-0007 dependency graph |

---

## 3. Exact Deliverables

By end of Week 1, the repository contains:

```
chronoarb/
├── pnpm-workspace.yaml
├── package.json                    # Root scripts (dev, lint, test, build)
├── turbo.json                      # Turborepo pipeline config
├── pyproject.toml                  # Python tool config (ruff, mypy, pytest)
├── .importlinter                   # ADR-0007 dependency enforcement
├── .github/
│   └── workflows/
│       └── ci.yml                  # Lint → type-check → test → build
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── compose.yaml                # PostgreSQL + Redis + LocalStack
├── apps/
│   ├── web/
│   │   ├── package.json            # next@16.2, react, tailwind, etc.
│   │   ├── tsconfig.json
│   │   ├── next.config.ts
│   │   ├── app/
│   │   │   ├── layout.tsx          # Minimal root layout
│   │   │   └── page.tsx            # Blank placeholder
│   │   └── lib/
│   │       └── api/                # Empty, awaiting generated client
│   ├── mobile/
│   │   ├── pubspec.yaml            # flutter, riverpod, go_router, etc.
│   │   ├── lib/
│   │   │   └── main.dart           # Minimal MaterialApp with placeholder
│   │   └── test/
│   │       └── widget_test.dart
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── apps/api/
│   │   │   ├── main.py             # FastAPI app with /health
│   │   │   ├── deps.py             # Dependency injection scaffold
│   │   │   └── middleware/
│   │   │       ├── tracing.py      # trace_id middleware
│   │   │       └── error_handler.py # Pydantic error → API envelope
│   │   └── tests/
│   │       └── test_health.py
│   └── worker/
│       ├── pyproject.toml
│       └── apps/worker/
│           ├── main.py             # Entry point with WORKER_TYPE env var
│           └── shared/
│               ├── sqs_client.py   # SQS wrapper skeleton
│               └── tracing.py      # OpenTelemetry skeleton
├── packages/
│   ├── domain-python/
│   │   ├── pyproject.toml
│   │   └── chronoarb/domain/
│   │       ├── __init__.py
│   │       ├── money.py            # Money, Currency value objects
│   │       ├── source_adapters/
│   │       │   └── protocol.py     # SourceAdapter Protocol (ADR-0007 D3)
│   │       └── errors.py           # Domain error hierarchy
│   ├── source-adapters/
│   │   ├── pyproject.toml
│   │   └── chronoarb/adapters/
│   │       └── __init__.py         # Empty; adapters added in Week 3-5
│   ├── api-client-ts/
│   │   ├── package.json            # Placeholder; generated client in Week 3
│   │   └── src/
│   │       └── index.ts            # Empty export
│   ├── api-client-dart/
│   │   ├── pubspec.yaml            # Placeholder; generated client in Week 3
│   │   └── lib/
│   │       └── api_client.dart     # Empty export
│   └── design-tokens/
│       ├── package.json
│       └── tokens/
│           └── colors.ts           # Placeholder palette
├── infrastructure/
│   └── terraform/
│       ├── main.tf                 # Provider + backend config
│       ├── variables.tf
│       ├── vpc.tf
│       ├── rds.tf
│       ├── elasticache.tf
│       ├── s3.tf
│       ├── ecr.tf
│       ├── ecs.tf
│       ├── sqs.tf
│       ├── cognito.tf
│       ├── iam.tf
│       ├── outputs.tf
│       └── environments/
│           ├── staging.tfvars
│           └── production.tfvars
└── alembic/
    ├── alembic.ini
    ├── env.py
    └── versions/
        └── 001_initial_schema.py   # All 22 tables per ADR-0002/0004/0005
```

---

## 4. Dependency Order

```
R01 Repository Foundation
   │
   ├──► R02 Python Toolchain ──► R04 Database Foundation
   │                                  │
   ├──► R03 TypeScript Toolchain      ├──► R06 Backend Skeleton
   │                                  │
   ├──► R05 Docker Foundation         ├──► R07 Worker Skeleton
   │                                  │
   └──────────────────────────────────┼──► R08 Frontend Skeletons
                                      │
                                      ├──► R09 Infrastructure Foundation
                                      │
                                      └──► R10 CI Pipeline (depends on all above)
```

---

## 5. Engineering Workstreams

### Workstream A: Repository Foundation

**Owner:** Infrastructure/DevOps engineer
**Objective:** Monorepo scaffolding with all tool configs and workspace orchestration.

| TaskID | Size | Task | Owner Module | Dependencies | Files Expected | Acceptance Criteria | Verification |
|--------|------|------|-------------|-------------|----------------|---------------------|-------------|
| WF-01 | XS | Initialize root `package.json` with workspace scripts | Root | None | `package.json`, `.npmrc` | `pnpm install` exits 0; `dev`, `lint`, `test`, `build` scripts defined | `pnpm install --frozen-lockfile` |
| WF-02 | XS | Create `pnpm-workspace.yaml` | Root | WF-01 | `pnpm-workspace.yaml` | Lists all `apps/*` and `packages/*`; `pnpm list -r` shows all workspaces | `pnpm list -r --depth=0` |
| WF-03 | Small | Create `turbo.json` with pipeline stages | Root | WF-02 | `turbo.json` | `build`, `lint`, `test`, `typecheck` pipeline stages defined; `dev` task with persistent flag | `pnpm turbo run build --dry-run` shows correct order |
| WF-04 | XS | Create root `tsconfig.base.json` | Root | WF-01 | `tsconfig.base.json` | Strict mode, ES2022 target, path aliases for `@chronoarb/*` | `pnpm exec tsc --showConfig --project tsconfig.base.json` |
| WF-05 | XS | Create root `pyproject.toml` with tool configs | Root | WF-01 | `pyproject.toml` | Ruff target-version=py313, mypy strict=true, pytest config, coverage config | `ruff check .` (no files yet), `mypy --version` |
| WF-06 | XS | Create `.importlinter` | Root | WF-05, ADR-0007 | `.importlinter` | Layers: domain-python, source-adapters, api, worker; forbidden rules per ADR-0007 D2 | `import-linter` passes (no imports yet) |
| WF-07 | XS | Create `.gitignore` and `.dockerignore` | Root | None | `.gitignore`, `.dockerignore` | Excludes `node_modules`, `__pycache__`, `.env*`, `.terraform`, `dist/`, lock files | `git status` shows no generated files |
| WF-08 | XS | Create `AGENTS.md` at `apps/api/` and `packages/domain-python/` | Root | AGENTS.md root | `apps/api/AGENTS.md`, `packages/domain-python/AGENTS.md` | Each references root AGENTS.md and adds module-specific rules | Files exist with correct authority order |

### Workstream B: Python Toolchain

**Owner:** Backend engineer
**Objective:** Python workspace with dependency management, linting, and type-checking.

| TaskID | Size | Task | Owner Module | Dependencies | Files Expected | Acceptance Criteria | Verification |
|--------|------|------|-------------|-------------|----------------|---------------------|-------------|
| WF-09 | XS | Create `packages/domain-python/pyproject.toml` | domain-python | WF-05 | `packages/domain-python/pyproject.toml` | Package name `chronoarb-domain`, Python >=3.13, no dependencies | `pip install -e packages/domain-python` |
| WF-10 | XS | Create `packages/source-adapters/pyproject.toml` | source-adapters | WF-09, ADR-0007 | `packages/source-adapters/pyproject.toml` | Depends on `chronoarb-domain` (editable) | `pip install -e packages/source-adapters` |
| WF-11 | XS | Create `apps/api/pyproject.toml` | api | WF-09 | `apps/api/pyproject.toml` | fastapi, uvicorn, sqlalchemy[asyncio], alembic, pydantic, asyncpg, httpx | `pip install -e apps/api` |
| WF-12 | XS | Create `apps/worker/pyproject.toml` | worker | WF-09, WF-10 | `apps/worker/pyproject.toml` | Depends on chronoarb-domain + chronoarb-adapters; aioboto3 (SQS stubs) | `pip install -e apps/worker` |
| WF-13 | XS | Create `domain-python/chronoarb/domain/` package skeleton | domain-python | WF-09 | `__init__.py`, `money.py`, `errors.py`, `source_adapters/__init__.py`, `source_adapters/protocol.py` | `Money(amount=Decimal, currency=str)` class, `SourceAdapter` Protocol with 5 methods, error hierarchy | `python -c "from chronoarb.domain.money import Money"` |

### Workstream C: TypeScript Toolchain

**Owner:** Frontend engineer
**Objective:** TypeScript workspace with Next.js, Tailwind, and shared packages.

| TaskID | Size | Task | Owner Module | Dependencies | Files Expected | Acceptance Criteria | Verification |
|--------|------|------|-------------|-------------|----------------|---------------------|-------------|
| WF-14 | XS | Create `apps/web/package.json` | web | WF-04 | `apps/web/package.json` | next@16.2, react@19, typescript, tailwindcss, @tanstack/react-query, react-hook-form, zod | `pnpm install --filter @chronoarb/web` |
| WF-15 | XS | Create `apps/web/tsconfig.json` | web | WF-04, WF-14 | `apps/web/tsconfig.json` | Extends `../../tsconfig.base.json`, includes `app/`, `components/`, `hooks/`, `lib/` | `pnpm exec tsc --project apps/web/tsconfig.json --noEmit` |
| WF-16 | XS | Create `packages/design-tokens/package.json` | design-tokens | None | `packages/design-tokens/package.json` | Empty package; `tokens/colors.ts` placeholder | `pnpm install --filter @chronoarb/design-tokens` |
| WF-17 | XS | Create `packages/api-client-ts/package.json` | api-client-ts | None | `packages/api-client-ts/package.json` | Placeholder; generated client path in `src/` | `pnpm install --filter @chronoarb/api-client` |

### Workstream D: Database Foundation

**Owner:** Backend engineer
**Objective:** Alembic configuration and initial migration defining all 22 tables incorporating ADR-0002, ADR-0004, and ADR-0005.

| TaskID | Size | Task | Owner Module | Dependencies | Files Expected | Acceptance Criteria | Verification |
|--------|------|------|-------------|-------------|----------------|---------------------|-------------|
| WF-18 | Small | Create Alembic configuration | api | WF-11 | `alembic.ini`, `alembic/env.py` | Uses async SQLAlchemy engine; reads `DATABASE_URL` from env; migration directory `alembic/versions/` | `alembic current` shows no migrations applied; `alembic upgrade head` runs |
| WF-19 | Medium | Write initial migration (all 22 tables) | api | WF-18, database-design.md, ADR-0002, ADR-0004, ADR-0005 | `alembic/versions/001_initial_schema.py` | All tables defined per database-design.md §2.1-2.12 with ADR corrections: ① alert_deliveries has `organization_id` + `material_version` columns, no composite UNIQUE; ② normalized_listings has `observation_at`, `fx_source`, `fx_date`; ③ junction tables have `created_at` | `alembic upgrade head` creates all 22 tables in PostgreSQL; `alembic downgrade -1` drops them |
| WF-20 | XS | Write `pg_ulid` helper for ULID generation | domain-python | WF-13 | `chronoarb/domain/ulid.py` | `generate_ulid(prefix)` returns `"org_01J..."`; prefix validation, sortability, uniqueness | `python -c "from chronoarb.domain.ulid import generate_ulid; assert generate_ulid('org').startswith('org_')"` |

### Workstream E: Backend Skeleton

**Owner:** Backend engineer
**Objective:** FastAPI application that starts, returns health, and demonstrates correct module structure.

| TaskID | Size | Task | Owner Module | Dependencies | Files Expected | Acceptance Criteria | Verification |
|--------|------|------|-------------|-------------|----------------|---------------------|-------------|
| WF-21 | Small | Create FastAPI application shell | api | WF-11, WF-13 | `apps/api/main.py`, `apps/api/deps.py`, `apps/api/middleware/tracing.py`, `apps/api/middleware/error_handler.py` | `/health` returns `{"status": "ok", "trace_id": "..."}` ; `/health/ready` checks DB; error handler maps Pydantic errors to API envelope | `curl http://localhost:8000/health` → 200 |
| WF-22 | XS | Create 12 backend module directories | api | WF-21 | 12 `apps/api/<module>/` dirs; each with `__init__.py`, `domain/`, `application/`, `infrastructure/`, `api/` subdirs | All directories exist per project-analysis.md §5; no implementation code | `find apps/api -type d | wc -l` ≥ expected count |
| WF-23 | XS | Create SQLAlchemy async engine and session factory | api | WF-21 | `apps/api/infrastructure/database.py` | AsyncEngine from `DATABASE_URL` env var; async sessionmaker; `get_db` dependency | `python -c "from apps.api.infrastructure.database import engine; print(engine)"` |

### Workstream F: Worker Skeleton

**Owner:** Backend engineer
**Objective:** Worker process that starts, reads `WORKER_TYPE`, and connects to queue stub.

| TaskID | Size | Task | Owner Module | Dependencies | Files Expected | Acceptance Criteria | Verification |
|--------|------|------|-------------|-------------|----------------|---------------------|-------------|
| WF-24 | Small | Create worker entry point | worker | WF-12, WF-23 | `apps/worker/main.py`, `apps/worker/shared/sqs_client.py`, `apps/worker/shared/tracing.py` | Reads `WORKER_TYPE` env var; starts loop; SQS client skeleton with receive/delete/dlq methods; OpenTelemetry skeleton | `WORKER_TYPE=discovery python -m apps.worker.main` logs "Worker discovery started" |
| WF-25 | XS | Create worker type registry | worker | WF-24 | `apps/worker/registry.py` | Maps `WORKER_TYPE` string to handler function; unknown type exits with error | `WORKER_TYPE=invalid python -m apps.worker.main` exits 1 |

### Workstream G: Frontend Skeletons

**Owner:** Web engineer + Flutter engineer
**Objective:** Web and mobile apps compile and serve placeholder pages.

| TaskID | Size | Task | Owner Module | Dependencies | Files Expected | Acceptance Criteria | Verification |
|--------|------|------|-------------|-------------|----------------|---------------------|-------------|
| WF-26 | Small | Create Next.js app shell | web | WF-14, WF-15 | `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`, `apps/web/next.config.ts`, `apps/web/tailwind.config.ts`, `apps/web/postcss.config.js` | `pnpm dev` serves page at localhost:3000; Tailwind classes compile; TypeScript compiles with strict mode | `pnpm --filter @chronoarb/web dev` → page loads |
| WF-27 | Small | Create Flutter app shell | mobile | None | `apps/mobile/pubspec.yaml`, `apps/mobile/lib/main.dart`, `apps/mobile/test/widget_test.dart` | `flutter create` baseline; riverpod, go_router, dio, freezed deps declared; compiles for iOS and Android | `cd apps/mobile && flutter build apk --debug` |
| WF-28 | XS | Create Flutter feature directory skeleton | mobile | WF-27 | `apps/mobile/lib/core/`, `apps/mobile/lib/features/` subdirs with `onboarding/`, `opportunities/`, `watches/`, `alerts/`, `activity/`, `settings/` | Structure matches frontend-design.md §2.1 | `find apps/mobile/lib -type d` matches expected |

### Workstream H: Docker Foundation

**Owner:** Infrastructure/DevOps engineer
**Objective:** Dockerfiles for all services and local Docker Compose.

| TaskID | Size | Task | Owner Module | Dependencies | Files Expected | Acceptance Criteria | Verification |
|--------|------|------|-------------|-------------|----------------|---------------------|-------------|
| WF-29 | Small | Create `Dockerfile.api` | api | WF-11, WF-21 | `docker/Dockerfile.api` | Multi-stage: build (pip install) → run (uvicorn); Python 3.13-slim base; non-root user | `docker build -f docker/Dockerfile.api -t chronoarb-api .` |
| WF-30 | XS | Create `Dockerfile.worker` | worker | WF-12, WF-24 | `docker/Dockerfile.worker` | Same base as API; CMD overridden by WORKER_TYPE | `docker build -f docker/Dockerfile.worker -t chronoarb-worker .` |
| WF-31 | Small | Create `docker/compose.yaml` | Root | WF-29, WF-30, WF-19 | `docker/compose.yaml` | Services: postgres (18), redis (valkey), localstack (SQS+S3), api, worker | `docker compose -f docker/compose.yaml up -d postgres redis localstack` |
| WF-32 | XS | Create `.env.example` | Root | WF-31 | `.env.example` | DATABASE_URL, REDIS_URL, AWS_ENDPOINT_URL (localstack), COGNITO_USER_POOL_ID placeholder, STRIPE_KEY placeholder | File exists with all required vars commented |

### Workstream I: Infrastructure Foundation

**Owner:** Infrastructure/DevOps engineer
**Objective:** Terraform modules for all AWS resources. Plan-only in Week 1 (no apply until staging env created).

| TaskID | Size | Task | Owner Module | Dependencies | Files Expected | Acceptance Criteria | Verification |
|--------|------|------|-------------|-------------|----------------|---------------------|-------------|
| WF-33 | Small | Create Terraform root module | infrastructure | None | `main.tf`, `variables.tf`, `outputs.tf`, `terraform.tf` | S3 backend (placeholder), AWS provider ~>5.0, region variable, environment tag | `terraform init` in `infrastructure/terraform/` |
| WF-34 | Medium | Create VPC module | infrastructure | WF-33 | `vpc.tf` | 2 AZs, public + private subnets, NAT gateway, flow logs | `terraform plan` shows VPC resources |
| WF-35 | Small | Create RDS module | infrastructure | WF-34 | `rds.tf` | PostgreSQL 18, db.t4g.medium (staging), encrypted, automated backups, 7-day retention | `terraform plan` shows RDS instance |
| WF-36 | Small | Create ElastiCache module | infrastructure | WF-34 | `elasticache.tf` | Redis 7/Valkey, small node type, encryption at rest, VPC-only | `terraform plan` shows ElastiCache cluster |
| WF-37 | XS | Create S3 module | infrastructure | WF-33 | `s3.tf` | Evidence bucket (KMS encrypted, versioned), artifact bucket | `terraform plan` shows S3 buckets |
| WF-38 | XS | Create ECR module | infrastructure | WF-33 | `ecr.tf` | Repos: api, worker; image scanning enabled; lifecycle policy (keep 10) | `terraform plan` shows ECR repos |
| WF-39 | Small | Create ECS module | infrastructure | WF-34, WF-35, WF-38 | `ecs.tf` | Fargate cluster, task defs for api + worker (placeholder images), service with ALB | `terraform plan` shows ECS resources |
| WF-40 | Small | Create SQS module | infrastructure | WF-34 | `sqs.tf` | 7 queues + 7 DLQs per system-design.md §4; redrive policy, 4-day retention | `terraform plan` shows 14 SQS queues |
| WF-41 | Small | Create Cognito module | infrastructure | WF-33 | `cognito.tf` | User pool, app client (auth code + PKCE), domain, JWT config | `terraform plan` shows Cognito resources |
| WF-42 | Small | Create IAM module | infrastructure | WF-34-WF-41 | `iam.tf` | ECS task roles (RDS, S3, SQS, Secrets Manager access), CI deploy role | `terraform plan` shows IAM roles |
| WF-43 | XS | Create environment variable files | infrastructure | WF-33 | `environments/staging.tfvars`, `environments/production.tfvars` | Staging: small instance sizes, soft delete; Production: backed-up, MFA-delete | `terraform plan -var-file=environments/staging.tfvars` |

### Workstream J: CI Pipeline

**Owner:** Infrastructure/DevOps engineer
**Objective:** GitHub Actions workflow that runs on every push and PR.

| TaskID | Size | Task | Owner Module | Dependencies | Files Expected | Acceptance Criteria | Verification |
|--------|------|------|-------------|-------------|----------------|---------------------|-------------|
| WF-44 | Medium | Create CI workflow | Root | WF-01-WF-43 | `.github/workflows/ci.yml` | Jobs: lint-python (ruff), lint-ts (eslint), typecheck-python (mypy), typecheck-ts (tsc), test-python (pytest), test-ts (vitest), build-web, import-linter, terraform-validate | Push to `main` or PR triggers all jobs; all pass | Push a branch → green CI |
| WF-45 | XS | Create `scripts/ci-lint.sh` | Root | WF-05 | `scripts/ci-lint.sh` | Runs `ruff check .` and `ruff format --check .` | `bash scripts/ci-lint.sh` exits 0 | Same |
| WF-46 | XS | Create `scripts/ci-test.sh` | Root | WF-05 | `scripts/ci-test.sh` | Runs `pytest apps/api/ apps/worker/ packages/` | `bash scripts/ci-test.sh` exits 0 | Same |

### Workstream K: Testing Foundation

**Owner:** Backend + Web engineers
**Objective:** Test configurations and placeholder tests that prove the pipeline works.

| TaskID | Size | Task | Owner Module | Dependencies | Files Expected | Acceptance Criteria | Verification |
|--------|------|------|-------------|-------------|----------------|---------------------|-------------|
| WF-47 | XS | Write `test_health.py` | api | WF-21 | `apps/api/tests/test_health.py` | Tests `GET /health` returns 200; `GET /health/ready` returns 200 or 503 | `pytest apps/api/tests/test_health.py` |
| WF-48 | XS | Write `test_money.py` | domain-python | WF-13 | `packages/domain-python/tests/test_money.py` | Tests `Money` creation, addition, subtraction, Decimal precision, currency mismatch error | `pytest packages/domain-python/tests/` |
| WF-49 | XS | Write `test_ulid.py` | domain-python | WF-20 | `packages/domain-python/tests/test_ulid.py` | Tests ULID prefix, uniqueness (1000 sequential), sortability (monotonic) | `pytest packages/domain-python/tests/` |
| WF-50 | XS | Write import-linter contract test | domain-python | WF-06, ADR-0007 | Tests in `.importlinter` config | import-linter verifies no forbidden imports exist | `import-linter` in CI |
| WF-51 | XS | Write widget test for Flutter placeholder | mobile | WF-27 | `apps/mobile/test/widget_test.dart` | Flutter default counter test works | `cd apps/mobile && flutter test` |

---

## 6. Tasks by Size

### XS Tasks (≤30 minutes each, 23 tasks)

| TaskID | Description | Workstream |
|--------|-------------|-----------|
| WF-01 | Root `package.json` | Repository |
| WF-02 | `pnpm-workspace.yaml` | Repository |
| WF-04 | Root `tsconfig.base.json` | Repository |
| WF-05 | Root `pyproject.toml` | Repository |
| WF-06 | `.importlinter` | Repository |
| WF-07 | `.gitignore` / `.dockerignore` | Repository |
| WF-08 | Module `AGENTS.md` files | Repository |
| WF-09 | `domain-python/pyproject.toml` | Python Toolchain |
| WF-10 | `source-adapters/pyproject.toml` | Python Toolchain |
| WF-11 | `apps/api/pyproject.toml` | Python Toolchain |
| WF-12 | `apps/worker/pyproject.toml` | Python Toolchain |
| WF-13 | `domain-python` package skeleton | Python Toolchain |
| WF-16 | `design-tokens/package.json` | TypeScript Toolchain |
| WF-17 | `api-client-ts/package.json` | TypeScript Toolchain |
| WF-20 | ULID helper | Database |
| WF-22 | 12 module directories | Backend |
| WF-23 | DB engine + session | Backend |
| WF-25 | Worker type registry | Worker |
| WF-28 | Flutter feature dirs | Frontend |
| WF-30 | `Dockerfile.worker` | Docker |
| WF-32 | `.env.example` | Docker |
| WF-37 | S3 module (Terraform) | Infrastructure |
| WF-38 | ECR module (Terraform) | Infrastructure |
| WF-43 | Environment tfvars | Infrastructure |
| WF-45 | `scripts/ci-lint.sh` | CI |
| WF-46 | `scripts/ci-test.sh` | CI |
| WF-47 | `test_health.py` | Testing |
| WF-48 | `test_money.py` | Testing |
| WF-49 | `test_ulid.py` | Testing |
| WF-50 | import-linter contract | Testing |
| WF-51 | Flutter widget test | Testing |

### Small Tasks (30-90 minutes each, 14 tasks)

| TaskID | Description | Workstream |
|--------|-------------|-----------|
| WF-03 | `turbo.json` pipeline | Repository |
| WF-14 | `apps/web/package.json` | TypeScript Toolchain |
| WF-15 | `apps/web/tsconfig.json` | TypeScript Toolchain |
| WF-18 | Alembic configuration | Database |
| WF-21 | FastAPI app shell | Backend |
| WF-24 | Worker entry point | Worker |
| WF-26 | Next.js app shell | Frontend |
| WF-27 | Flutter app shell | Frontend |
| WF-29 | `Dockerfile.api` | Docker |
| WF-31 | `docker/compose.yaml` | Docker |
| WF-33 | Terraform root module | Infrastructure |
| WF-35 | RDS module (Terraform) | Infrastructure |
| WF-36 | ElastiCache module (Terraform) | Infrastructure |
| WF-39 | ECS module (Terraform) | Infrastructure |
| WF-40 | SQS module (Terraform) | Infrastructure |
| WF-41 | Cognito module (Terraform) | Infrastructure |
| WF-42 | IAM module (Terraform) | Infrastructure |

### Medium Tasks (90-180 minutes each, 3 tasks)

| TaskID | Description | Workstream |
|--------|-------------|-----------|
| WF-19 | Initial database migration (all 22 tables) | Database |
| WF-34 | VPC module (Terraform) | Infrastructure |
| WF-44 | CI workflow (GitHub Actions) | CI |

---

## 7. What Is NOT Implemented in Week 1

These items are explicitly out of scope and must not be started:

| Category | Not Implemented | Will Be Done |
|----------|----------------|-------------|
| **Business logic** | Any API endpoint beyond `/health` and `/health/ready` | Week 3-5 |
| **Models** | SQLAlchemy model classes (only migration SQL this week) | Week 2-3 |
| **Repositories** | Repository implementations with tenant scoping | Week 3-5 |
| **Services** | Domain service classes or use-case orchestration | Week 3-5 |
| **Auth** | JWT validation middleware, Cognito integration | Week 3-5 |
| **Routes** | Any customer-facing routes (opportunities, alerts, catalog, etc.) | Week 3+ |
| **Workers** | Worker pipeline logic (discovery, fetch, normalize, etc.) | Week 3-5 |
| **Adapters** | Source adapter implementations (only Protocol this week) | Week 3-5 |
| **Web UI** | Any page beyond blank placeholder (no login, no dashboard) | Week 9-10 |
| **Mobile UI** | Any screen beyond blank placeholder | Week 11-12 |
| **Billing** | Stripe integration, webhooks | Week 13 |
| **Telegram** | Bot integration | Week 6-8 |
| **E2E tests** | Playwright or integration_test suites | Week 9+ |
| **Secrets** | Real AWS secrets, API keys, tokens | Week 1 uses placeholder env vars only |
| **Terraform apply** | Any AWS resource creation | Plan-only until staging env is ready |

---

## 8. Risks for Week 1

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| pnpm lockfile conflicts across OS (macOS vs Linux) | Medium | Low | Pin pnpm version in `package.json.engines`; use `--frozen-lockfile` in CI |
| PostgreSQL 18 not available in AWS RDS or Docker image | Low | Medium | Verify PostgreSQL 18 availability; fall back to 17.x in Terraform with documented justification |
| Python 3.13.x availability in Docker image | Low | Low | Use `python:3.13-slim-bookworm` or equivalent; confirm before building |
| Flutter 3.44.x not released yet | High | High | Pin to latest stable 3.x release available; document version mismatch with SRS; create ADR for version decision |
| Turborepo caching conflicts with pnpm in CI | Low | Medium | Configure `turbo.json` with `cache: true` and remote caching disabled for Week 1 |
| Import boundary violations not detectable yet | Low | Low | import-linter only flags actual violations; with just Protocol defined and no adapter imports, this will pass trivially |
| Team blocked by missing local dev environment | Medium | Medium | WF-31 (Docker Compose) is a priority task for Day 2; engineers can use local Python/Node until then |
| Monorepo tooling choice not approved | Medium | Low | Turborepo is recommended but pnpm workspaces alone works for Week 1; ADR for tooling can be created during the week |
| Alembic migration generator vs hand-written migration | Low | Low | WF-19 is hand-written to match the explicit schema from database-design.md; not using `--autogenerate` for initial migration |

---

## 9. Decisions Resolved by ADRs (Week 1 Relevance)

The following architecture questions have been resolved and are directly implemented in Week 1:

| ADR | Decision | Week 1 Implementation |
|-----|----------|----------------------|
| ADR-0001 D1 | Modular monolith + async workers | WF-22 creates 12 module dirs; WF-24 creates worker skeleton |
| ADR-0001 D3 | Decimal for money | WF-13 `Money` class uses `Decimal` |
| ADR-0001 D4 | ULID primary keys | WF-20 creates ULID helper; WF-19 migration uses TEXT PKs |
| ADR-0001 D6 | Idempotency keys | WF-19 migration has `idempotency_key TEXT UNIQUE NOT NULL` on feedbacks, alert_deliveries, trade_outcomes |
| ADR-0001 D7 | Tenant isolation | WF-19 migration has `organization_id` on all tenant tables |
| ADR-0001 D9 | Source adapter isolation | WF-13 Protocol in domain-python; WF-10 source-adapters depends on domain-python |
| ADR-0001 D10 | Immutable records | WF-19 migration has `model_version`, `config_version` on valuations; no UPDATE triggers for immutable tables |
| ADR-0002 | alert_deliveries schema | WF-19 migration includes `organization_id`, `material_version`, no composite UNIQUE |
| ADR-0003 | In-process WebSocket | No WebSocket code in Week 1; architecture decision recorded for Week 9 |
| ADR-0004 | data_age / observation_at | WF-19 migration adds `observation_at TIMESTAMPTZ` to normalized_listings |
| ADR-0005 | FX provenance | WF-19 migration adds `fx_source TEXT`, `fx_date DATE` to normalized_listings |
| ADR-0006 | Web auth flow | No auth code in Week 1; Redis session pattern documented for Week 3 |
| ADR-0007 | Package dependencies | WF-06 `.importlinter` with complete dependency graph; WF-50 contract test |

---

## 10. Week 1 Verification Checklist

Before marking Week 1 complete, verify every item:

```
[ ] pnpm install --frozen-lockfile                     # All workspaces resolve
[ ] pnpm turbo run lint --dry-run                       # Pipeline graph is correct
[ ] ruff check .                                        # Zero Python lint errors
[ ] mypy packages/domain-python/                        # Zero type errors
[ ] mypy apps/api/                                      # Zero type errors (health endpoint only)
[ ] pnpm --filter @chronoarb/web exec tsc --noEmit      # Zero TS errors
[ ] alembic upgrade head                                # All 22 tables created
[ ] alembic downgrade -1                                # Reverses cleanly
[ ] uvicorn apps.api.main:app                           # /health returns 200
[ ] WORKER_TYPE=discovery python -m apps.worker.main     # Logs "Worker discovery started"
[ ] pnpm --filter @chronoarb/web dev                    # Page at localhost:3000
[ ] cd apps/mobile && flutter build apk --debug         # Build succeeds
[ ] docker compose -f docker/compose.yaml up -d          # All services start
[ ] docker compose -f docker/compose.yaml exec api curl localhost:8000/health  # 200
[ ] terraform init && terraform validate                 # No config errors
[ ] terraform plan -var-file=environments/staging.tfvars # Clean plan output
[ ] pytest apps/api/ apps/worker/ packages/              # All tests pass
[ ] import-linter                                        # No forbidden imports
[ ] pnpm turbo run build                                 # All packages build
[ ] gh workflow run ci.yml && gh run watch               # CI green on GitHub
```

---

## 11. Engineering Assignments (Recommended Split)

| Engineer | Primary Workstreams | Secondary |
|----------|-------------------|-----------|
| Backend/Data #1 | Python Toolchain (WF-09-13), Database (WF-18-20), Backend (WF-21-23) | Testing (WF-47-50) |
| Backend/Data #2 | Worker (WF-24-25), Terraform SQS/IAM (WF-40,42) | Docker (WF-29-32) |
| DevOps | Repository (WF-01-08), Docker (WF-29-32), Infrastructure (WF-33-43), CI (WF-44-46) | — |
| Web | TypeScript Toolchain (WF-14-17), Frontend Web (WF-26) | Testing Web |
| Flutter | Frontend Mobile (WF-27-28), Testing Mobile (WF-51) | — |

**Parallel pairs for Day 1:**
- DevOps + Backend #2: Monorepo scaffolding (WF-01-08) + Docker (WF-29-32) — these are independent
- Backend #1: Domain skeleton (WF-09-13) — no dependencies on repo setup beyond WF-05
- Web + Flutter: Can begin app shells independently after WF-01/02 are done
