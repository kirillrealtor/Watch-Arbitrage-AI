# ChronoArb AI-Agent Engineering Rules

This file is the default instruction set for every AI coding agent working in the ChronoArb repository. More specific `AGENTS.md` files may exist inside `apps/`, `packages/`, or `infrastructure/`; the nearest file to the code being edited adds to these rules but cannot weaken security, tenant isolation, financial correctness, or SRS requirements.

## 1. Authority order

When instructions conflict, follow this order:

1. Applicable law, source agreements, payment-provider rules, and app-store rules.
2. `ChronoArb_MVP_SRS_v1.0` and approved requirement changes.
3. Approved Architecture Decision Records in `docs/adr/`.
4. This `AGENTS.md` and the nearest module-level `AGENTS.md`.
5. The current task packet and acceptance criteria.
6. Existing implementation patterns.

Do not silently reinterpret an SRS requirement. Record ambiguity in the task packet and either ask for a decision or create an ADR proposal.

## 2. Product and architecture invariants

- The MVP is dealer-acquisition intelligence, not a marketplace, custody service, authentication service, or automated purchasing system.
- The customer-facing backend is a FastAPI modular monolith. Ingestion, normalization, valuation, alert matching, and notification work run in separate worker processes and queues.
- PostgreSQL is the system of record. Redis/Valkey is never the sole source of truth.
- Raw evidence, normalized listings, predictions, user decisions, and realized outcomes remain distinct layers.
- Financial calculations use `Decimal`/fixed-point values and explicit currency codes. Binary floating point is prohibited for money.
- Every tenant-scoped read and write must be authorized and constrained by `organization_id`.
- Queue consumers, webhooks, feedback writes, and notification sends must be idempotent.
- Customer-visible estimates must include data age, confidence, valuation version, and the cost-assumption version.
- No source integration may bypass authentication walls, CAPTCHAs, rate limits, or contractual restrictions.
- No source-specific parsing logic may enter core catalog, valuation, opportunity, alert, or UI modules.
- No code path may claim guaranteed authenticity, availability, or profit.

## 3. Token-efficient operating procedure

Before editing code:

1. Read this file.
2. Read the task packet and its acceptance criteria.
3. Read the nearest module `README.md` and `AGENTS.md`.
4. Search for existing components, hooks, services, repositories, schemas, tests, and utilities before creating new ones.
5. Open only the files named by the task or discovered through targeted search. Do not load entire directories, lock files, generated clients, or large fixtures unless the task requires them.
6. Produce a short plan when the task touches more than three production files, changes a contract/schema, or introduces a dependency.

During implementation:

- Make the smallest coherent change that satisfies the task.
- Prefer editing existing abstractions over creating parallel ones.
- Do not rewrite whole files when a focused patch is sufficient.
- Run the narrowest relevant tests first, then the required module and repository gates.
- Keep a context ledger: files read, assumptions made, commands run, and unresolved questions.

At completion, report only:

- Requirements and acceptance criteria satisfied.
- Files changed and why.
- Tests/checks run and results.
- Migrations, feature flags, rollout notes, or operational effects.
- Remaining risks or explicit follow-ups.

Keep handoffs under 600 words unless a production incident or architecture change requires more detail.

## 4. Task sizing and stop conditions

A normal task should have one primary outcome, one owning module, and verifiable acceptance criteria. Split work when it crosses unrelated modules or exceeds roughly ten production files, one database migration, or one deployable behavior change.

Stop and request clarification or an ADR when:

- The SRS and task conflict.
- A source-access method is not approved.
- A change weakens tenant isolation, authentication, financial accuracy, auditability, or idempotency.
- A dependency or architectural boundary must change.
- A destructive migration or irreversible data rewrite is proposed.
- Acceptance criteria cannot be objectively verified.

## 5. Reuse and duplication rules

- Business rules, financial formulas, permission checks, state transitions, event names, and API contracts must have one authoritative implementation.
- Search before creating. Reuse an existing component/hook/service only when its semantics match; do not force unrelated behavior into a generic abstraction.
- Extract repeated business logic immediately. For presentational UI, use the rule of three unless the repeated pattern is already a defined design-system primitive.
- Prefer composition over large configurable “god” components.
- Generated OpenAPI clients and generated model files are never edited by hand.
- Constants that affect product behavior must be named, documented, versioned when needed, and tested. No unexplained magic numbers.

## 6. Cross-stack quality rules

- Strict type checking is mandatory in TypeScript, Dart, and Python.
- Public functions, exported components, providers, services, and domain objects require clear names and concise documentation when intent is not obvious.
- No swallowed exceptions, empty catch blocks, debug prints, commented-out code, placeholder secrets, or permanent TODOs without an issue reference.
- Errors shown to users are actionable and safe. Internal details go to structured logs with a trace ID.
- Network calls have explicit timeouts, cancellation where relevant, bounded retries, and retry classification.
- Every changed behavior has tests at the lowest effective layer.
- Security, accessibility, observability, and migration impacts are part of implementation, not post-build cleanup.

## 7. Next.js rules

- Use the App Router and React Server Components by default for stable shells and initial server-rendered data.
- Add `"use client"` only at the smallest interactive boundary.
- Components render UI; hooks coordinate client-side behavior; API modules perform transport; domain/view-model functions transform data.
- UI components must not call `fetch`, generated API clients, or browser storage directly.
- Server state lives in TanStack Query. Do not mirror it into global client state.
- Forms use React Hook Form and Zod at external boundaries.
- Shared primitives belong in the design system; feature components remain inside their feature.
- Every async screen implements loading, empty, error, stale, and success states.
- Maintain keyboard navigation, visible focus, semantic HTML, accessible labels, and WCAG 2.2 AA behavior.
- Never make authorization decisions from client feature flags or hidden UI.

## 8. Flutter rules

- Organize by feature. Each feature separates presentation, application/controller, domain, and data responsibilities.
- Widgets do not call Dio, secure storage, Drift, Firebase, or repositories directly.
- Riverpod providers expose dependencies and state; notifiers/controllers coordinate use cases; repositories own remote/local data behavior.
- Transport DTOs are mapped into domain models before reaching UI.
- Use immutable models and exhaustive sealed states for loading/data/empty/error/offline behavior.
- Navigation uses typed/declarative `go_router` routes. Deep links restore authentication and organization context before opening protected content.
- Tokens live only in secure platform storage. Sensitive data is not written to logs or unencrypted preferences.
- Every user-visible feature supports dynamic text, VoiceOver/TalkBack semantics, adequate touch targets, and offline behavior defined by the SRS.

## 9. FastAPI and Python rules

- Routes handle HTTP concerns only: validation, authentication dependency, authorization entry, service call, response mapping.
- Domain services contain use-case orchestration. Repositories own persistence queries. Pure domain functions contain formulas and policies.
- SQLAlchemy models are not returned directly from API routes.
- Pydantic request/response schemas are versioned through the API contract.
- Repository methods that access tenant data require an explicit tenant/organization scope.
- Use transactions around state transitions and outbox/event creation that must commit atomically.
- External calls are behind typed gateways/adapters and are mocked through interfaces in tests.
- Async code must not perform blocking I/O on the event loop.
- Use Ruff formatting/linting, mypy or approved strict type checking, pytest, and import-boundary checks.

## 10. Data, queues, and source adapters

- Preserve immutable raw evidence before parsing when permitted.
- Identical evidence plus the same parser version must produce deterministic output.
- Each adapter declares source key, version, access mode, rate/concurrency policy, approval reference, stable IDs, fixtures, and health assertions.
- Jobs carry correlation/trace IDs and idempotency keys.
- At-least-once queue delivery must not create duplicate logical listings, predictions, opportunities, or notifications.
- Poison messages go to a DLQ with enough metadata for replay; never loop forever.
- Matching and valuation outputs store method, features, model/config versions, confidence, and lineage.

## 11. Database and migration rules

- Use UUID/ULID-style opaque identifiers consistently with the existing schema.
- Use `numeric`/decimal for money and UTC timestamps for storage.
- Add indexes based on real query paths and verify plans for high-volume feeds.
- Production migrations follow expand/contract: add compatible structures, deploy compatible code, backfill safely, then remove old structures in a later release.
- Migrations are forward-only in production. Every migration has a staging rehearsal and a documented recovery strategy.
- Backfills are resumable, observable, rate limited, and do not hold long table locks.

## 12. Security and privacy rules

- Deny by default. Enforce RBAC and tenant scope server-side on every protected operation.
- Validate JWT issuer, audience, signature, expiry, and membership.
- Verify webhook signatures and prevent replay.
- Allowlist outbound source domains; do not fetch customer-supplied arbitrary URLs.
- Secrets come from Secrets Manager or approved local secret tooling and never enter source control, images, mobile bundles, analytics, or logs.
- Minimize user, seller, Telegram, device, and financial-outcome data. Follow approved retention and deletion rules.
- Privileged actions create immutable audit events.

## 13. Testing and release gates

Changed code must pass the relevant subset of:

- Unit and property-based tests for formulas, policies, parsers, matching, permissions, and state transitions.
- Component/widget tests for UI behavior and accessibility.
- Contract tests for OpenAPI, adapters, Stripe, Telegram, FCM, and source fixtures.
- Integration tests for PostgreSQL, S3, SQS, Redis/Valkey, OIDC, and webhooks.
- End-to-end tests for critical dealer and operations journeys.
- Tenant-isolation, SSRF, webhook replay, dependency, secret, and container security checks.
- Performance checks for feed queries, worker throughput, WebSocket fanout, and alert latency when affected.

A task is not done until code, tests, documentation, observability, migration/rollout needs, and acceptance evidence are complete.

## 14. Required completion format

Use this exact structure in the final handoff:

```text
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
