# ChronoArb — Project Analysis

**Document type:** Product analysis and MVP boundary definition
**Source documents:** ChronoArb_MVP_SRS_v1.0, AI-Agent Engineering Playbook v1.0
**Date:** 2026-08-03

---

## 1. Product Understanding

### 1.1 What ChronoArb Is

ChronoArb is a **dealer-acquisition intelligence platform** for luxury watch dealers. It ingests listings from approved third-party sources, normalizes them to a canonical catalog, computes all-in acquisition costs and expected resale values, and alerts dealers to arbitrage opportunities.

The core value proposition: **"Should I buy this watch at this price?"** — answered with traceable data, not speculation.

### 1.2 Target Users

- **Primary:** Professional luxury watch dealers who buy from multiple online sources and resell through known exit channels.
- **Secondary:** Operations staff who manage sources, catalog, and data quality.
- **Target:** At least 10 design partners during beta; commercial conversion post-MVP.

### 1.3 Core User Outcome

A dealer receives an actionable alert: a listing from an approved source is priced materially below its estimated executable exit value after all acquisition costs and risk reserves. The dealer can review the opportunity with full cost waterfall, comparables, confidence indicators, and data lineage — then record a decision.

### 1.4 Primary Action

Dealer opens an opportunity alert → reviews cost breakdown and comps → records PURCHASED, CONTACTED, or DISMISSED.

---

## 2. MVP Boundaries

### 2.1 In Scope

| Dimension | MVP Scope |
|-----------|-----------|
| Supported references | 25 active canonical watch references |
| Production sources | 3 approved sources with recorded legal/business review |
| Web application | Next.js dealer dashboard (opportunity feed, detail, alerts, settings, activity) |
| Mobile application | Flutter iOS/Android (feed, detail, push notifications, offline feedback queue) |
| Catalog system | Canonical references, brands, variants, aliases, source mappings |
| Ingestion pipeline | Source discovery → fetch → parse → normalize → deduplicate |
| Valuation engine | Comparable-based with condition/set/geography adjustments, risk reserves |
| Alert engine | Rule matching by reference/price/condition with cooldowns |
| Notification channels | Telegram bot, FCM push (mobile) |
| Identity | OIDC (Cognito), organization membership, RBAC (Owner/Admin/Dealer/Viewer) |
| Billing | Stripe Billing with trial/paid/cancel/past-due entitlement states |
| Operations tools | Source health, job replay, DLQ management, admin queues |
| Multi-tenancy | Organization-scoped data with strict tenant isolation |

### 2.2 Explicit Non-Goals (MVP)

These are recorded from the SRS and must not be built during MVP:

- Marketplace or transaction platform (no custody, no escrow, no money movement between parties)
- Automated purchasing system (no bot checkout, no balance-sheet inventory)
- Authentication service for third parties (no watch authentication claims)
- Stripe Connect or marketplace payment architecture
- Enterprise SSO / advanced team workflows
- Portfolio or inventory tracking for dealers
- Negotiation support or seller communication templates
- Verified-opportunity workflow with independent authentication and insured logistics
- Continuous GPS location tracking
- Customer-supplied arbitrary URL fetching

### 2.3 Deferred to V1.1 / V2

- Additional references and regional sources based on revenue per reference
- Enterprise SSO, advanced team workflows, data exports/API access
- Improved image similarity and supervised condition extraction
- Portfolio and inventory tracking
- Negotiation support and seller communication
- Verified-opportunity workflow
- Marketplace platform (requires separate legal, risk, and custody program)

---

## 3. Architecture Decisions

Decisions below are **engineering recommendations** derived from the SRS and playbook. Decisions marked **[NEEDS APPROVAL]** require explicit stakeholder sign-off.

### 3.1 Sourced from Documents (Authoritative)

| Decision | Source |
|----------|--------|
| FastAPI modular monolith for customer-facing backend | SRS §7.1 |
| Separate worker processes for ingestion, normalization, valuation, alerts, notifications | SRS §2, §7.1 |
| PostgreSQL as system of record; Redis/Valkey never sole source of truth | SRS §2, §7.1 |
| Decimal/fixed-point for all financial calculations; no binary floating point | SRS §2 |
| Organization-scoped queries with explicit `organization_id` | SRS §2 |
| Idempotent queue consumers, webhooks, feedback writes, notifications | SRS §2 |
| Source-specific parsing logic never in core catalog/valuation/opportunity/alert/UI | SRS §2 |
| No path claims guaranteed authenticity, availability, or profit | SRS §2 |
| AWS infrastructure: ECS Fargate, RDS PostgreSQL 18, ElastiCache, S3, Cognito, SQS, FCM, Stripe | SRS §7.2 |
| Monorepo: apps/web, apps/mobile, apps/api, apps/worker, packages/, infrastructure/ | SRS §7.3 |
| OWASP ASVS 5.0 Level 2 security baseline | SRS §11.1 |
| Immutable raw evidence before parsing where permitted | SRS §10 |
| Deterministic parser output for identical evidence | SRS §10 |

### 3.2 Engineering Recommendations

| Decision | Rationale |
|----------|-----------|
| Python 3.13.x (not 3.14.6) | SRS recommends 3.13.x for conservative dependency compatibility; 3.14 is bleeding edge |
| Alembic for migrations with expand/contract pattern | Required by SRS §11 and playbook §13.2 |
| Ruff for formatting/linting, mypy for strict type checking | Required by playbook §11.6 |
| Pydantic v2 for API schemas with generated OpenAPI | Required by SRS §9 |
| SQLAlchemy 2.0 async for repository implementations | Matches FastAPI async pattern |
| TanStack Query v5 for web server state | Required by AGENTS.md §7 |
| React Hook Form + Zod for web forms | Required by AGENTS.md §7 |
| Riverpod + freezed for Flutter state management | Required by AGENTS.md §8 |
| go_router for Flutter navigation | Required by SRS §9.2 |
| Drift with encryption for mobile offline cache | Required by SRS §9.2 |
| Playwright Python for E2E tests | Required by SRS §8.5 |
| Vitest for web unit tests | Compatible with Next.js/TypeScript |
| GitHub Actions for CI/CD | Required by SRS §7.2 |
| Terraform for IaC | Required by SRS §7.2, §13.1 |
| Docker BuildKit for container images | Required by SRS §7.2 |
| OpenTelemetry for observability | Required by SRS §7.2 |

### 3.3 Decisions Requiring Approval

| Decision | Stakeholders | Context |
|----------|-------------|---------|
| **[NEEDS APPROVAL]** Which three sources to integrate first | Product/Legal | Must be approved for access mode, terms, rate limits, display/retention |
| **[NEEDS APPROVAL]** Which 25 canonical watch references to support | Product/Domain experts | Affects catalog schema, valuation calibration, and dealer onboarding |
| **[NEEDS APPROVAL]** Amazon Cognito vs alternative OIDC provider | Engineering/Security | SRS permits Cognito or equivalent; selection affects API auth patterns |
| **[NEEDS APPROVAL]** SQS FIFO vs standard queues per queue | Engineering | FIFO guarantees exactly-once but has throughput limits; standard + idempotency may suffice |
| **[NEEDS APPROVAL]** Monorepo tooling: Turborepo vs Nx vs pnpm workspaces | Engineering | Affects CI setup, caching, cross-package scripts |
| **[NEEDS APPROVAL]** WebSocket implementation: in-process vs dedicated service | Engineering | SRS requires WebSocket for real-time updates; scaling model differs |
| **[NEEDS APPROVAL]** Weekly or daily ingestion schedules per source | Product/Operations | Affects worker scaling and cost |

---

## 4. Monorepo Structure

```
chronoarb/
├── apps/
│   ├── web/                    # Next.js 16 App Router (TypeScript)
│   ├── mobile/                 # Flutter 3.44 (Dart)
│   ├── api/                    # FastAPI entry point (Python)
│   └── worker/                 # Worker process entry points (Python)
├── packages/
│   ├── domain-python/          # chronoarb.domain — pure business logic
│   ├── source-adapters/        # chronoarb.adapters — source-specific fetch/parse
│   ├── api-client-ts/          # Generated TypeScript API client
│   ├── api-client-dart/        # Generated Dart API client
│   └── design-tokens/          # Shared visual tokens, icons, themes
├── infrastructure/
│   └── terraform/              # AWS infrastructure as code
├── docker/                     # Dockerfiles and compose files
├── docs/
│   ├── reference/              # SRS, playbook, source approval records
│   ├── architecture/           # System, database, API, frontend, worker, security designs
│   ├── adr/                    # Architecture Decision Records
│   ├── runbooks/               # Operational runbooks
│   ├── api/                    # OpenAPI spec and generated docs
│   └── tests/                  # Test strategy and fixture documentation
└── scripts/                    # CI, local dev, and data scripts
```

### 4.1 Module Dependency Rules

```
apps/api        → packages/domain-python
apps/worker     → packages/domain-python, packages/source-adapters
apps/web        → packages/api-client-ts, packages/design-tokens
apps/mobile     → packages/api-client-dart, packages/design-tokens
```

- `packages/domain-python` MUST NOT import from `packages/source-adapters` or any `apps/` package.
- `packages/source-adapters` MUST NOT import from `apps/` packages.
- Core modules (catalog, valuation, opportunities) MUST NOT import source-specific code.
- No circular dependencies between packages.

---

## 5. Backend Modules (FastAPI)

Defined by SRS §10.1. Each module follows the playbook structure: `domain/`, `application/`, `infrastructure/`, `api/`.

| Module | Responsibility |
|--------|----------------|
| identity | JWT validation, user provisioning, organization memberships, RBAC |
| catalog | Brands, references, variants, aliases, source mappings, watch lists |
| sources | Source configuration, adapter registry, schedules, job lifecycle, health |
| listings | Logical listings, raw snapshots, price history, status |
| normalization | Reference matching, attribute extraction, geography, FX, confidence |
| duplicates | Candidate generation, similarity scoring, representative selection |
| valuation | Comparable selection, adjustments, cost model, ranges, model versioning |
| opportunities | Scoring, lifecycle, material versions, explanations, user views |
| alerts | Rule CRUD, matching engine, cooldowns, channel routing, delivery status |
| feedback | Decisions (PURCHASED/CONTACTED/DISMISSED), trade outcomes, metrics |
| billing | Stripe customer mapping, webhook state, entitlements |
| operations | Admin queues, feature flags, audits, support tools |

---

## 6. Technology Baseline

| Concern | Technology | Version |
|---------|-----------|---------|
| Web | Next.js App Router, TypeScript, Tailwind CSS | 16.2.x |
| Mobile | Flutter, Dart | 3.44.x |
| API | FastAPI, Python | 3.13.x |
| Database | PostgreSQL (AWS RDS) | 18.x |
| Cache | Redis/Valkey (AWS ElastiCache) | Current |
| Queue | Amazon SQS | — |
| Object storage | Amazon S3 | — |
| Identity | Amazon Cognito (or approved OIDC) | — |
| Push | Firebase Cloud Messaging | — |
| Billing | Stripe Billing + Checkout + Customer Portal | — |
| Compute | AWS ECS Fargate | — |
| CDN/Edge | CloudFront, ALB, WAF | — |
| IaC | Terraform | — |
| CI | GitHub Actions | — |

---

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Source access changes or blocks | Coverage gap, detection speed degradation | Prefer contracts/APIs; adapter isolation; diversify sources; kill switch; fallback feeds |
| Asking-price bias | False opportunity, customer trust loss | Executable exit values calibrated against realized outcomes; risk reserves |
| Wrong reference/variant classification | Severe false positive on high-value watches | Reference-specific rules; confidence thresholds; manual review queue; per-reference quality gates |
| Hidden condition in photos/text | Margin disappears after inspection | Risk reserves; Unknown condition state; evidence snippets displayed; no authentication claim |
| Cross-post duplicates | Inflated supply, repeated alerts | Image/text/seller duplicate grouping; representative suppression |
| Stale/phantom listings | Wasted dealer time, missed real deals | Availability scoring; freshness decay; user feedback loop; source-specific staleness policies |
| Notification latency | Dealer loses time-sensitive opportunity | Priority queues; provider monitoring; Telegram + push redundancy; alert SLO tracking |
| Subscription churn | Low revenue retention | Design-partner onboarding; narrow liquid references; proof-of-value reporting |
| Data leakage | Dealer strategy/outcomes exposed | Tenant isolation; staff least privilege; audit; security testing |
| Mobile billing rejection | App store launch delay | Existing-entitlement companion approach; current policy/legal review before submission |
| Cloud/source cost growth | Poor SaaS gross margin | Per-source cost dashboard; adaptive schedules; revenue-based coverage decisions |
| Overbuilding marketplace features | Capital/legal risk, distraction from SaaS | Formal stage gate; brokerage excluded from MVP |

---

## 8. Testing Strategy

| Level | Scope | Tool |
|-------|-------|------|
| Unit | Financial formulas, scoring, permissions, parsers, matching rules, state transitions | pytest, Vitest, flutter_test |
| Property-based | Money invariants, normalization, idempotency, pagination | Hypothesis |
| Contract | Source adapter fixtures, OpenAPI clients, Stripe/Telegram/FCM interfaces | pytest |
| Integration | PostgreSQL, S3, SQS, Redis/Valkey, OIDC, webhooks | pytest |
| End-to-end | Onboarding, alert creation, opportunity open, feedback, billing, admin | Playwright |
| Mobile integration | Push deep links, offline queue, session restore | integration_test |
| Performance | Feed/API load, queue throughput, source concurrency, WebSocket | k6/Artillery |
| Security | SAST/DAST, dependency, tenant isolation, auth abuse, SSRF, webhook replay | Trivy, Semgrep |
| Accessibility | WCAG 2.2 AA automated + manual review | Axe, VoiceOver/TalkBack |
| Operational | Restore drills, kill switches, DLQ replay, incident game days | Manual + scripted |
