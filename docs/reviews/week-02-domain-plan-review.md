# Week 02 — Domain Plan Review

**Review type:** Pre-implementation architecture audit
**Reviewed document:** docs/implementation/week-02-domain-plan.md
**Date:** 2026-08-03T17:50:20+05:00
**Reviewer:** Architecture review pass
**Cross-referenced:** database-design.md, security-model.md, api-design.md, AGENTS.md

---

## Executive Summary

The Week 2 plan is technically sound in its repository architecture, tenant isolation patterns, and ORM model strategy. However, one architectural issue requires correction: services that orchestrate repositories belong in the `application/` layer, not `domain/`. The established 4-subdirectory module structure (`domain/`, `application/`, `infrastructure/`, `api/`) was created in Batch 2 and must be respected. Placing services in `domain/` violates the layer dependency rules and creates coupling between domain logic and infrastructure concerns.

**Verdict: APPROVED WITH CORRECTIONS**

---

## 1. ORM Model Boundaries

### Per-Module Model Organization

The plan organizes models per-module (10 files for 25 tables) rather than a single monolithic model file.

**Assessment:** PASS. This matches the established module structure from Batch 2 and enforces ADR-0007 cross-module import isolation. Each module owns its models.

### Immutable Entity Handling

| Table | Has `updated_at`? | Plan Correct? |
|-------|-------------------|---------------|
| `valuations` | No (immutable) | YES — direct `created_at`, no TimestampMixin |
| `raw_snapshots` | No (immutable) | YES — no `updated_at` in migration DDL |
| `opportunities` | No (new version = new row) | YES — correct pattern |

**Finding:** The plan correctly identifies 3 tables as immutable and excludes `TimestampMixin`. The `opportunities` table has `state_changed_at` and `published_at` which are tracking timestamps set at creation time, not UPDATE timestamps.

**PASS.**

### Model File Count

The plan specifies 10 model files for 25 tables. Let me verify the distribution:

| File | Tables | Count |
|------|--------|-------|
| identity/models.py | organizations, users, memberships | 3 |
| catalog/models.py | brands, references, aliases, watch_lists, watch_list_entries, sources | 6 |
| listings/models.py | raw_snapshots, parsed_listings, normalized_listings, duplicate_groups, duplicate_group_members | 5 |
| valuation/models.py | valuations | 1 |
| opportunities/models.py | opportunities, opportunity_views | 2 |
| alerts/models.py | alert_rules, alert_deliveries | 2 |
| feedback/models.py | feedbacks, trade_outcomes | 2 |
| billing/models.py | subscriptions | 1 |
| operations/models.py | audit_events, outbox_events, feature_flags | 3 |
| **Total** | | **25** |

25 tables across 9 model files — the plan says 10. `infrastructure/models.py` (Base, TimestampMixin) already exists, so the plan may be counting it. Minor discrepancy.

**PASS.**

---

## 2. Repository Architecture

### Base Class Design

The `BaseRepository[Model]` and `TenantRepository[Model]` generic pattern is clean. The `organization_id` parameter is mandatory on all `TenantRepository` methods — no optional default.

**Assessment:** PASS. The type signature itself enforces tenant scoping. Any call site that forgets `organization_id` gets a `TypeError` at code analysis time (mypy strict mode).

### Repository Count

The plan says "18 repositories" in the written summary. Let me count the inventory table entries:

1. OrganizationRepository
2. UserRepository
3. MembershipRepository
4. BrandRepository
5. ReferenceRepository
6. WatchListRepository
7. SourceRepository
8. ListingRepository
9. DuplicateRepository
10. ValuationRepository
11. OpportunityRepository
12. AlertRuleRepository
13. AlertDeliveryRepository
14. FeedbackRepository
15. TradeOutcomeRepository
16. SubscriptionRepository
17. AuditEventRepository
18. OutboxEventRepository
19. FeatureFlagRepository

**Issue CR-01: Repository count mismatch — 19 repositories, plan says 18.** (MINOR)

**Action:** Update the plan text to "19 repositories."

### Cursor Pagination Helpers

The cursor pagination example uses `encode_cursor()` and `decode_cursor()` functions that are not defined in the plan. These need a documented location.

**Issue CR-02: `encode_cursor`/`decode_cursor` location not specified.** (NOTE)

**Action:** Add these to `apps/api/apps/api/infrastructure/repository.py` alongside the base classes, or create `apps/api/apps/api/infrastructure/pagination.py`.

---

## 3. Tenant Isolation Enforcement

### Mandatory organization_id Pattern

```python
# ✅ Plan example — correct
async def get_by_id(self, id: str, organization_id: str) -> Model | None:
```

**Assessment:** PASS. The `organization_id` parameter has no default value — it's mandatory. This is the correct "impossible to forget" pattern from ADR-0001 D7.

### Cross-Tenant Protection

The plan states: "If the row exists but belongs to a different organization, return `None` (not 403)." This prevents information leakage — an attacker cannot distinguish "doesn't exist" from "exists but isn't yours."

**Assessment:** PASS. This matches the security-model.md tenant isolation pattern: cross-tenant access must produce 404 (not found), not 403 (forbidden).

### Global Data Access

Non-tenant tables (sources, references, normalized_listings, valuations) use `BaseRepository` — no `organization_id` parameter. This is correct — pipeline data is shared.

**Assessment:** PASS.

---

## 4. Transaction Boundaries

### Outbox Co-Location

The service example shows outbox event creation in the same transaction as the state change:

```python
async def create_organization(self, cmd: CreateOrganizationCommand) -> Organization:
    async with self.uow:
        await self.org_repo.save(org)
        await self.outbox_repo.save(event)
        await self.uow.commit()
```

**Assessment:** PASS. The outbox event and the state change commit atomically. If either fails, both roll back. This guarantees at-least-once event publishing.

### Unit of Work Abstraction

The plan references `self.uow` (Unit of Work) but doesn't define its interface. The UoW appears to wrap a session + outbox repository + commit. This needs a concrete definition before implementation.

**Issue CR-03: Unit of Work interface not defined.** (NOTE)

**Action:** Define `UnitOfWork` class in `apps/api/apps/api/infrastructure/uow.py` or document that services receive `AsyncSession` directly and use `session.commit()` — keeping it simpler for Week 2.

---

## 5. Service Boundaries

### Service Placement

**Issue CR-04: Services placed in `domain/` instead of `application/`.** (MAJOR)

The plan states (line 243): "Services live in each module's `domain/` directory."

The established module structure from Batch 2 has 4 subdirectories per module:
- `domain/` — pure business logic (entities, value objects, policies, formulas)
- `application/` — use-case orchestration (services, commands, queries)
- `infrastructure/` — persistence (models, repositories, external gateways)
- `api/` — HTTP concerns (routes, middleware, schemas)

The plan's services call repositories, manage transactions, and write outbox events. These are application-layer concerns — they depend on infrastructure (repositories) and orchestrate infrastructure access. Placing them in `domain/` violates the dependency direction:

```
domain MUST NOT depend on infrastructure
But services in domain/ depend on repositories (infrastructure)
→ VIOLATION
```

**Correct placement:** `application/services.py` or `application/{service_name}.py`

**Example:**
```
identity/
├── domain/           # OrganizationPolicy (pure business rules)
├── application/      # OrganizationService (calls repos, orchestrates use cases)
├── infrastructure/   # OrganizationModel, OrganizationRepository
└── api/              # Organization routes (Week 3-5)
```

**Action:** Move all service references from `domain/services.py` to `application/services.py`. The `domain/` directory remains for pure domain logic (policy objects, formula functions) that will be implemented in Week 3-5.

### Service Count

The plan defines 6 services for Week 2:

| Service | Assessment |
|---------|------------|
| `OrganizationService` | Correct — CRUD + member management |
| `MembershipService` | Correct — role assignment, validation |
| `CatalogService` | Correct — read-only reference and brand data |
| `WatchListService` | Correct — CRUD for watch lists |
| `OpportunityFeedService` | Correct — feed query with cursor pagination |
| `AlertRuleService` | Correct — CRUD for alert rules |

**PASS** (count and responsibilities are correct; placement needs correction).

---

## 6. Pydantic Schema Strategy

### Schema File Location

The plan's file manifest in §10 lists no Pydantic schema files. The plan references `OrganizationResponse` and `ValuationResponse` but doesn't specify where they live.

**Issue CR-05: Pydantic schema file locations not specified.** (MINOR)

Schemas are API-layer concerns — they should live in `api/` subdirectories per the module structure:

```
identity/api/schemas.py    # OrganizationResponse, MembershipResponse
catalog/api/schemas.py     # ReferenceResponse, BrandResponse
opportunities/api/schemas.py # OpportunityResponse, OpportunityFeedResponse
```

**Action:** Add Pydantic schema files to the §10 file manifest.

### snake_case Compliance

The plan doesn't explicitly mandate `snake_case` for Pydantic field names, but this is inherited from the api-design.md conventions and the existing schemas.py (HealthResponse, ApiError). No risk of drift.

**PASS.**

---

## 7. Testing Coverage

### Tenant Isolation Tests

The plan mandates cross-tenant isolation tests for every tenant-scoped repository. The example test pattern is correct:
- Create data for org A
- Query with org B's ID → expect None
- Query with org A's ID → expect data

**PASS.**

### Test Database

The conftest.py example uses `sqlite+aiosqlite://` for testing. PostgreSQL-specific features (ENUMs, JSONB, NUMERIC precision) cannot be validated against SQLite.

**Issue CR-06: SQLite test database cannot validate PostgreSQL-specific features.** (NOTE)

Models with ENUM columns or JSONB fields will work differently on SQLite (ENUMs become TEXT, JSONB becomes TEXT). Tests against SQLite verify application logic but not schema correctness. Schema-correctness tests require PostgreSQL (CI Python 3.13 leg).

**Action:** Document that CI validates against PostgreSQL. Local tests validate application logic only.

### Test File Count

The plan lists 8 test files. Coverage across:
- Repositories: identity, catalog, opportunity, alert
- Cross-cutting: tenant isolation, cursor pagination
- Services
- All 19 repositories are covered by at least one test file

**PASS.**

---

## 8. Module Dependency Rules (ADR-0007)

### Cross-Module Model Imports

The plan organizes models per-module with no cross-module imports. Each module's `infrastructure/models.py` imports only from `apps/api/infrastructure/models.py` (Base, TimestampMixin) and SQLAlchemy.

**Assessment:** PASS. This prevents the "import everything" anti-pattern and enforces ADR-0007 module isolation.

### Repository Cross-Module Imports

The `ListingRepository` provides read access to `raw_snapshots`, `parsed_listings`, and `normalized_listings`. A service in another module (e.g., feedback service needing normalized listing data) would import the repository, not the model directly.

**Assessment:** PASS. This is the correct dependency pattern — services import repositories, not models.

---

## 9. Migration Compatibility

### Model-Schema Validation

The plan states: "Creating a test that instantiates each model and verifies `Base.metadata.create_all()` does not produce schema drift from the migration-defined DDL."

**Assessment:** PASS. This is the correct validation approach. `Base.metadata.create_all()` generates DDL from ORM models. Comparing it against the migration DDL catches model-schema drift.

### Risk: ENUM and JSONB on SQLite

`Base.metadata.create_all()` against SQLite will not produce the same DDL as the PostgreSQL migration. ENUM columns become TEXT, JSONB columns become TEXT, and NUMERIC becomes plain NUMERIC without PostgreSQL-specific modifiers. The validation test must run against PostgreSQL.

**Action:** Model-schema validation test runs in CI on the Python 3.13 PostgreSQL leg. Local validation is for application logic only.

---

## 10. Additional Findings

### File Path Convention

The plan uses `apps/api/apps/api/` (double `apps/api/`) as the module root. This is correct — it matches the `pyproject.toml` package declaration `packages = ["apps"]`. The import path is `from apps.api.identity.infrastructure.models import Organization`. Correct.

### `source-adapters` Package Not Touched

The plan does not create any code in `packages/source-adapters/`. This is correct — source adapters are implemented in Week 3-5 with concrete source integrations. The `SourceAdapter` Protocol from Batch 2 remains the only code in that package.

### `packages/domain-python` Not Extended

The plan does not extend `packages/domain-python`. The existing `Money`, `generate_ulid`, and `DomainError` are sufficient for Week 2. New domain objects (policies, formulas) will be added in Week 3-5 when business logic is implemented.

**PASS.**

---

## 11. Correction Summary

| ID | Severity | Description | Location | Action |
|----|----------|-------------|----------|--------|
| CR-01 | MINOR | Repository count mismatch: plan says 18, actual count is 19 | §4.3 summary | Update text to "19 repositories" |
| CR-02 | NOTE | `encode_cursor`/`decode_cursor` helper location not specified | §4.4 | Add to `infrastructure/repository.py` or create `infrastructure/pagination.py` |
| CR-03 | NOTE | Unit of Work interface not defined | §5.3 | Define UoW or simplify to direct session usage |
| CR-04 | MAJOR | Services placed in `domain/` — should be in `application/` | §5.1, §10 | Move all `services.py` from `domain/` to `application/` |
| CR-05 | MINOR | Pydantic schema file locations not in manifest | §10 | Add `identity/api/schemas.py`, `catalog/api/schemas.py`, etc. |
| CR-06 | NOTE | SQLite test DB cannot validate PostgreSQL ENUM/JSONB | §8.2 | Document CI PostgreSQL validation as the schema correctness gate |

---

## 12. Batch Progression Gate

**Question: Is the Week 2 plan ready for implementation?**

Yes, with one required correction. CR-04 (service placement) must be corrected before any implementation code is written — placing services in `domain/` would create an architectural violation that would require refactoring.

| Gate | Status |
|------|--------|
| ORM model boundaries correct | PASS |
| Repository architecture sound | PASS |
| Tenant isolation enforced | PASS |
| Transaction boundaries correct | PASS |
| Immutable entity handling correct | PASS |
| Service boundaries | **PENDING CR-04** (move to application/) |
| Pydantic schema strategy | PASS (locations need documenting) |
| Testing coverage adequate | PASS |
| Module dependency rules enforced | PASS |
| Migration compatibility verified | PASS |

**Verdict: APPROVED WITH CORRECTIONS**

CR-04 is the only gate-blocking issue. CR-01 through CR-06 (excluding CR-04) are documentation or minor clarifications that can be resolved during implementation without structural changes.
