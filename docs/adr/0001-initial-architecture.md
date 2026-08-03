# ADR-0001: Initial Architecture

**Status:** Proposed
**Date:** 2026-08-03
**Deciders:** Lead Software Architect
**Supersedes:** None

---

## Context

ChronoArb is a greenfield project. The SRS (ChronoArb_MVP_SRS_v1.0) defines the product as a dealer-acquisition intelligence platform. The Engineering Playbook specifies the technology stack, module boundaries, and quality gates. No architecture decisions have been recorded yet.

We must establish the foundational architecture decisions before writing any production code.

---

## Decision

### D1: Modular Monolith + Async Workers

The customer-facing backend shall be a single FastAPI application (modular monolith). Long-running ingestion, normalization, valuation, alert matching, and notification work shall execute in separate worker processes driven by SQS queues.

**Rationale:**
- Modular monolith provides fast development, simple deployment, and easy testing while maintaining module boundaries.
- Async workers isolate CPU/IO-intensive pipeline stages and allow independent scaling.
- Aligns with SRS §7.1 and AGENTS.md §2 invariants.

**Alternatives considered:**
- Microservices — Rejected for MVP. Adds network latency, deployment complexity, and distributed-systems overhead without sufficient scale justification.
- Single process — Rejected. Cannot scale pipeline stages independently and risks API availability during heavy ingestion.

### D2: PostgreSQL as Sole System of Record

PostgreSQL shall be the single authoritative data store. Redis/Valkey shall only store short-lived cache, rate counters, distributed locks, and WebSocket fanout state.

**Rationale:**
- Strong consistency guarantees for financial data.
- ACID transactions for atomic state changes + outbox events.
- Redis as ephemeral cache avoids dual-write consistency problems.
- Aligns with SRS §2 invariant: "Redis/Valkey is never the sole source of truth."

### D3: Decimal/Fixed-Point for All Financial Values

All monetary calculations shall use Python's `Decimal` type and PostgreSQL `NUMERIC` columns. Binary floating point (float/double) is prohibited for any value representing money.

**Rationale:**
- Floating point cannot precisely represent decimal currency values (e.g., 0.10 cannot be represented exactly in binary).
- Errors compound across multi-step acquisition cost and resale calculations.
- Aligns with AGENTS.md §2 invariant.

### D4: Opaque ULID Primary Keys

All database tables shall use ULID-style identifiers (e.g., `org_01J...`, `lst_01J...`) with a type prefix rather than auto-increment integers or raw UUIDs.

**Rationale:**
- Sortable by time (unlike UUIDv4) — beneficial for feed pagination and range queries.
- Opaque — prevents enumeration attacks and information leakage.
- Type prefix improves debugging and log readability.
- Collision-resistant across distributed workers.
- Aligns with SRS §11: "UUID/ULID-style opaque identifiers."

### D5: Expand/Contract Migration Strategy

All production database migrations shall follow the expand/contract pattern: add compatible structures → deploy compatible code → backfill → cut over → remove old structures.

**Rationale:**
- Zero-downtime schema changes.
- Rollback capability until cutover is verified.
- Aligns with playbook §13.2 and SRS §13.4.

### D6: Idempotency by Design

Queue consumers, webhooks, feedback writes, and notification sends shall all use idempotency keys or unique database constraints to guarantee exactly-once logical effect under at-least-once delivery.

**Rationale:**
- SQS standard queues provide at-least-once delivery; idempotency prevents duplicates.
- Financial feedback and billing webhooks must not create duplicate records.
- Aligns with AGENTS.md §2 and playbook §12.3.

### D7: Tenant Isolation via Mandatory organization_id

Every repository method that accesses tenant data shall require an explicit `organization_id` parameter. Cross-tenant access shall produce 404 (not 403) to prevent information leakage.

**Rationale:**
- Dealer strategies and outcomes are commercially sensitive.
- "Impossible to forget" pattern prevents authorization bugs.
- Aligns with AGENTS.md §2 and playbook §11.4.

### D8: Contract-First Development

API schemas (Pydantic → OpenAPI), event envelopes, and source adapter interfaces shall be defined and tested before implementation begins.

**Rationale:**
- Enables parallel web and mobile development.
- Contract tests catch breaking changes in CI.
- Aligns with playbook §18.2.

### D9: Source Adapter Isolation

Source-specific parsing logic shall never enter core catalog, valuation, opportunity, alert, or UI modules. Adapters implement a shared Protocol and are registered via configuration.

**Rationale:**
- Adding/removing/modifying sources must not risk core valuation correctness.
- Adapters can be tested independently with saved fixtures.
- Aligns with AGENTS.md §2 and SRS §10.

### D10: Immutable Evidence and Versioned Outputs

Raw source observations shall be stored immutably before parsing. All pipeline outputs (parsed listings, normalized listings, valuations, opportunities) shall be immutable records with explicit version fields.

**Rationale:**
- Reproducible pipelines enable debugging and model evaluation.
- Immutable records enable lineage tracing from source to alert.
- Versioning enables safe model upgrades without affecting historical records.
- Aligns with playbook §12 and AGENTS.md §10.

### D11: Monorepo Structure

The repository shall follow the structure defined in SRS §7.3: `apps/` (web, mobile, api, worker), `packages/` (domain-python, source-adapters, api-client-ts, api-client-dart, design-tokens), `infrastructure/` (terraform), `docker/`, `docs/`.

**Rationale:**
- Single version control simplifies cross-package changes.
- Shared packages prevent code duplication.
- Aligns with SRS specification.

---

## Consequences

### Positive

- Clear module boundaries prevent architectural erosion.
- Idempotency prevents duplicate alerts and financial records.
- Tenant isolation reduces risk of data leakage.
- Immutable records enable full auditability and model evaluation.
- Contract-first enables parallel development across teams.

### Negative

- Modular monolith requires discipline to maintain module boundaries (mitigated by import-linter in CI).
- Expand/contract migrations add planning overhead per change.
- Decimal arithmetic requires explicit precision management.
- ULID generation is slightly more complex than UUID or auto-increment.

### Risks

- SQS FIFO queues (if chosen for some workloads) have throughput limits that may affect notification latency.
- Cognito selection may need re-evaluation if enterprise SSO requirements arrive early.
- Source adapter contract may need evolution as more diverse sources are added; this should be a minor version change, not a breaking one.

---

## References

- ChronoArb_MVP_SRS_v1.0: §7 Architecture, §10 Backend, §11 Security
- AI-Agent Engineering Playbook v1.0: §11 Backend Rules, §12 Ingestion Rules, §13 Database Rules, §14 Security Rules
- AGENTS.md: §2 Product and Architecture Invariants
