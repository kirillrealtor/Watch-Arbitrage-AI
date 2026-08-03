# ChronoArb — Architecture Review

**Review type:** Pre-implementation architecture audit
**Reviewed documents:** AGENTS.md, project-analysis.md, system-design.md, database-design.md, api-design.md, frontend-design.md, worker-design.md, security-model.md, development-roadmap.md, adr/0001-initial-architecture.md
**Date:** 2026-08-03
**Reviewer:** Architecture review pass
**Severity key:** BLOCKER > MAJOR > MINOR > NOTE

---

## Confirmed Decisions

The following decisions are sound and consistent across documents:

| Decision | Where | Assessment |
|----------|-------|------------|
| Modular monolith + async workers | ADR D1, system-design §1 | Correct for MVP scale. No contradiction. |
| PostgreSQL sole system of record | ADR D2, database-design §1 | Correct. Redis limited to cache/locks/fanout. |
| Decimal/fixed-point for money | ADR D3, worker-design §3.4 | All docs consistently enforce this. |
| ULID opaque primary keys | ADR D4, database-design §1 | Consistent across all tables. |
| Expand/contract migrations | ADR D5, database-design §4 | Well-documented and consistently referenced. |
| Idempotency by design | ADR D6, worker-design §4, api-design §5 | Consistently applied across all pipeline stages. |
| Tenant isolation via mandatory organization_id | ADR D7, security-model §3.2, system-design §7 | Correctly designed. Pattern is enforced. |
| Source adapter isolation | ADR D9, project-analysis §4.1 | Dependency rules prevent source code from entering core modules. |
| Immutable records + versioned outputs | ADR D10, database-design §2.6-2.7 | valuations and opportunities are immutable. Correct. |
| Contract-first development | ADR D8, roadmap §5 | Correct sequencing priority. |
| Monorepo with apps/packages split | ADR D11, project-analysis §4 | Structure is clear and matches SRS. |
| RBAC five-role model | security-model §3.1 | Matches SRS Appendix A. |
| OWASP ASVS 5.0 Level 2 | security-model §1 | Stated as baseline. |

---

## Issues Found

### BLOCKER-01: alert_deliveries table references non-existent column `material_version`

**File:** database-design.md line 244

```sql
UNIQUE(rule_id, user_id, opportunity_id, channel, material_version)
```

The `material_version` column is not defined on `alert_deliveries`. It exists on `opportunities` but is not joined or stored here. The unique constraint would fail at migration time.

**Fix:** Either:
- Add `material_version INT NOT NULL` column to `alert_deliveries` (populated from opportunity at match time)
- Use a partial index or join-based constraint
- Remove from UNIQUE and enforce idempotency solely via the already-present `idempotency_key TEXT UNIQUE NOT NULL` column

The `idempotency_key` column (which is `SHA256(org + user + rule + opp + material_version + channel)`) already encodes material version in its value. The UNIQUE on `material_version` is redundant. The `idempotency_key UNIQUE` constraint is sufficient for idempotency.

**Recommendation:** Remove the composite UNIQUE constraint. The `idempotency_key TEXT UNIQUE NOT NULL` alone provides the guarantee. The column `material_version` should still be added for query performance.

---

### BLOCKER-02: WebSocket design is unresolved and listed as "Needs Approval"

**Files:** project-analysis.md §3.3, api-design.md §3.10, system-design.md diagram

The architecture defines a WebSocket endpoint (`wss://api.chronoarb.com/ws`) but does not decide whether WebSocket connections terminate on the FastAPI service or a dedicated service. The system diagram shows WebSocket connected to neither.

**Impact:** If WebSocket is in-process with FastAPI:
- Horizontal scaling requires sticky sessions (ALB stickiness)
- Workers cannot push directly to connected clients — they must go through API
- Memory pressure from concurrent connections

If dedicated WebSocket service:
- Additional infrastructure (ECS service, scaling config)
- API ↔ WebSocket communication path needed
- Different auth model for JWT validation

**Recommendation:** Create ADR-0002 for WebSocket architecture decision. For MVP, recommend in-process FastAPI WebSocket with Redis pub/sub for worker-to-WebSocket fanout, since expected concurrent connections are low (design partners only).

---

### MAJOR-01: Customer-visible estimates missing required fields from AGENTS.md

**File:** api-design.md, database-design.md §2.7

AGENTS.md §2 requires: "Customer-visible estimates must include data age, confidence, valuation version, and the cost-assumption version."

The opportunity response schema is not fully specified in api-design.md, but the database-design.md shows:
- `valuations.confidence` ✓
- `valuations.model_version` ✓ (valuation version)
- `valuations.cost_assumptions_version` ✓
- **Missing:** `data_age` — How old is the listing observation? This should be derived from `raw_snapshots.fetched_at` or `parsed_listings.listed_at` and surfaced in API responses.

**Fix:** Add `data_age` to opportunity and valuation API response schemas. Document it as the delta between current time and the listing observation timestamp.

---

### MAJOR-02: No FX rate source/date tracking

**File:** database-design.md line 145

`normalized_listings.fx_rate NUMERIC(18,8)` stores the exchange rate but does not capture:
- `fx_source` — Which provider/service provided the rate
- `fx_date` — When the rate was obtained

**Impact:** Financial traceability is incomplete. If an incorrect FX rate produces wrong profit calculations, there's no way to identify which rate was used or when.

**Fix:** Add `fx_source TEXT` and `fx_date TIMESTAMPTZ` (or rename `fx_rate` to include these). This aligns with the "version everything" principle in ADR D10.

---

### MAJOR-03: No authentication design for Next.js → FastAPI

**Files:** api-design.md, frontend-design.md, system-design.md

The authentication flow for the web application is underspecified:
- System diagram shows Next.js connections to FastAPI, but Next.js does not have a back-end service
- API requests from the browser (client components) must include JWT in Authorization header
- The JWT needs to reach the browser via secure cookie → client-side extraction → Authorization header
- Or Next.js must proxy API calls through server-side route handlers (adding latency)

The SRS §8.1 says: "Next.js route handlers are limited to web-only edge concerns such as OIDC callbacks, secure cookie exchange and redirects."

**Decision needed:** Does the web app:
1. Call FastAPI directly from browser with JWT from cookie (requires non-httpOnly cookie or readable cookie + in-memory storage)?
2. Proxy through Next.js server with server-side token injection?

**Recommendation:** Option 1 with pattern: Cognito callback → Next.js route handler exchanges code → stores access token in httpOnly cookie → browser components use a server endpoint to read token into memory on page load → TanStack Query attaches Bearer token to all API calls. This avoids proxying all API traffic through Next.js.

---

### MAJOR-04: `packages/source-adapters` dependency on `packages/domain-python` missing

**File:** project-analysis.md §4.1

The dependency rules state:
```
apps/worker → packages/domain-python, packages/source-adapters
```

But the `SourceAdapter` Protocol interface definition must live in `domain-python` (as it's a core contract). Source adapters must implement this Protocol, requiring:
```
packages/source-adapters → packages/domain-python
```

This dependency is missing from the declared rules.

**Fix:** Add `packages/source-adapters → packages/domain-python` to the dependency graph. This is a one-directional dependency (adapters depend on domain contracts, never the reverse). The constraint "domain-python MUST NOT import from source-adapters" remains valid.

---

### MAJOR-05: `alert_deliveries` missing `organization_id`

**File:** database-design.md lines 234-244

`alert_deliveries` is tenant-scoped data (a delivery for a specific user in a specific organization), but it lacks `organization_id`. While it can be resolved through `rule_id → alert_rules.organization_id`, this violates the pattern of direct tenant scoping on every tenant-data table.

**Impact:** Any query that needs to list all deliveries for an organization requires a JOIN through alert_rules. This adds query complexity and creates a risk of missing the tenant filter.

**Fix:** Add `organization_id FK → organizations.id NOT NULL` to `alert_deliveries`.

---

### MAJOR-06: No data age / observation timestamp in normalized_listings

**File:** database-design.md lines 132-147

`normalized_listings` has `created_at` (when normalization happened) but does not expose the original observation time. For "data age" calculation, the system needs `parsed_listings.listed_at` or `raw_snapshots.fetched_at`.

The ER chain is: `raw_snapshots.fetched_at` → `parsed_listings` → `normalized_listings` → `valuations` → `opportunities`.

The opportunity API response must include data age, but this requires traversing 4 joins to compute.

**Fix:** Add `observation_at TIMESTAMPTZ` to `normalized_listings` (populated from `MIN(raw_snapshots.fetched_at, parsed_listings.listed_at)`) or add it to `valuations` directly. This denormalization is justified for a frequently-accessed field.

---

### MINOR-01: Inconsistent route naming — `/catalog/watch-lists` vs `/watches`

**File:** api-design.md

The API groups watch-list management under `/catalog/watch-lists` but market data under `/watches/{ref_id}/market`. The web route map in frontend-design.md shows `/watches` as the primary catalog page. This split creates confusion:
- `GET /catalog/watch-lists` — manage lists
- `GET /watches/{ref_id}/market` — view market data

**Fix:** Either move watch-lists under `/watches/lists` or rename watches to `/catalog` consistently. The SRS §8.2 shows both `/watches` and `/watches/[id]` as web routes, suggesting `/watches` as the primary namespace.

---

### MINOR-02: No `updated_at` on `watch_list_entries`, `duplicate_group_members`

**File:** database-design.md

Several junction/associative tables lack timestamps:
- `watch_list_entries` — no `created_at`
- `duplicate_group_members` — no `created_at`

While not functionally blocking, this is inconsistent with other tables and complicates audit/debugging.

**Fix:** Add `created_at TIMESTAMPTZ DEFAULT NOW()` to all junction tables.

---

### MINOR-03: Valuation input `listing_id` points to wrong entity

**File:** database-design.md line 173

```sql
valuations.listing_id FK → normalized_listings.id
```

This is actually correct — valuations operate on normalized_listings. But the field name `listing_id` is ambiguous given `parsed_listings` also represent listings. 

**Fix:** No functional issue, but consider renaming to `normalized_listing_id` for clarity, matching the pattern used elsewhere.

---

### MINOR-04: Worker lifecycle `raise` on TransientError is ambiguous

**File:** worker-design.md line 51

```python
except TransientError:
    # Visibility timeout will retry
    raise
```

The `raise` here re-raises the exception out of the message processing loop. This would crash the worker process (or be caught by an outer handler). The correct behavior for transient SQS failures is to NOT delete the message — the visibility timeout will make it reappear.

**Fix:** Change to `continue` (skip deletion, let message return to queue via timeout) or explicitly `pass` to avoid the raise. The comment correctly describes the intent but the code doesn't match.

---

### MINOR-05: Cursor pagination on dynamic `score` field

**File:** api-design.md §4, database-design.md §2.7

The opportunity feed sorts by `score` which is a computed, dynamic field. Cursor pagination on a mutable sort key has a known race condition: newly inserted/updated opportunities can appear or disappear mid-pagination, causing skipped or duplicated results.

**Recommendation:** Use `published_at` as the primary sort key with `score` as a secondary tiebreaker. For cursor pagination, encode `(published_at, id)` as the cursor, not score. The feed can still display in score-descending order if the `published_at` cursor anchors the pagination window.

---

### NOTE-01: `raw_snapshots.raw_payload` storage strategy ambiguous

**File:** database-design.md line 111

```sql
raw_payload JSONB (or S3 key reference)
```

The "or" indicates an undecided storage strategy. This affects:
- Row size (JSONB has practical limits)
- Query patterns (can't search S3-stored payloads)
- Cost (S3 is cheaper for large blobs)

**Recommendation:** For MVP, store everything as JSONB in PostgreSQL with a size limit (e.g., 1MB). If individual payloads exceed this, use a threshold-based approach: <1MB → JSONB, ≥1MB → S3 with key stored in `s3_key TEXT` column. Make `s3_key` the preferred pattern and deprecate JSONB storage for raw payloads in v1.1.

---

### NOTE-02: 8 worker types may exceed MVP needs

**File:** worker-design.md §1

For 25 references and 3 sources with ~10 design partners, eight separate worker types is architecturally clean but operationally heavy. Each worker type needs:
- Separate ECS task definition
- Separate scaling configuration
- Separate CloudWatch log group
- Separate deployment pipeline consideration

**Recommendation:** Combine for MVP: fetch+parse into one worker (they're tightly coupled), and consider merging alert_match into the notification flow. Use the `WORKER_TYPE` env var pattern already in the design to run different worker types from the same image.

---

### NOTE-03: No health-check endpoint defined

**File:** api-design.md

Missing `GET /health` or similar endpoint for ALB target group health checks, ECS health checks, and Kubernetes-style readiness/liveness probes.

**Fix:** Add:
- `GET /health` — Returns 200 if API process is running (liveness)
- `GET /health/ready` — Returns 200 if database and Redis are reachable (readiness)

---

### NOTE-04: No local development environment specification

Multiple docs reference "Docker Compose" and "saved source fixtures" but there's no concrete specification for the local development setup:
- Which services run in Docker vs natively?
- How are queues simulated locally? (LocalStack? ElasticMQ? In-memory stub?)
- How are workers run locally? (Same process? Separate terminals?)
- How is Cognito simulated? (Local mock?)

**Recommendation:** Create `docs/architecture/local-development.md` specifying the Docker Compose service set, environment variable template, and fixture management.

---

### NOTE-05: Telegram integration missing webhook endpoint

**File:** api-design.md, security-model.md

The security model mentions webhook signature verification (generic) but only Stripe webhooks are explicitly defined in the API. Telegram bots can operate in two modes:
1. **Polling (getUpdates)** — Simpler, no public endpoint needed. Good for MVP.
2. **Webhook** — Requires a public HTTPS endpoint, signature verification, replay protection.

**Recommendation:** Use polling mode for MVP Telegram integration. This eliminates the need for a public webhook endpoint, simplifies security, and is appropriate for low-volume MVP usage. Document this decision.

---

### NOTE-06: API success response envelope inconsistent with single-resource GETs

The API envelope shows `{ "data": { ... }, "meta": { ... } }`. For paginated collections, `meta` includes `next_cursor` and `has_more`. For single-resource GETs (e.g., `GET /opportunities/{id}`), should `meta` be omitted or contain only `trace_id`?

**Recommendation:** Always include `meta.trace_id`. For single-resource responses, omit `next_cursor` and `has_more` (they're null-omitted, not present=false).

---

### NOTE-07: No mention of api-client-dart in dependency rules

**File:** project-analysis.md §4.1

The dependency rules document `apps/mobile → packages/api-client-dart` but `api-client-dart` is not in the package listing in §4. It IS in the monorepo tree (line 150) but not in the dependency matrix. This is a documentation gap, not an architecture gap.

**Fix:** Add `packages/api-client-dart` to the dependency listing. Same for `packages/api-client-ts` which is also missing from the explicit dependency listing.

---

## Recommended Changes

### Immediate (before any code is written)

1. **Fix alert_deliveries schema** — Remove invalid UNIQUE constraint; use `idempotency_key` alone. [BLOCKER-01]
2. **Resolve WebSocket architecture** — Create ADR-0002. Recommend in-process for MVP. [BLOCKER-02]
3. **Add data_age to API responses** — Required by AGENTS.md §2. Add `observation_at` denormalized field. [MAJOR-01]
4. **Add FX rate source/date tracking** — `fx_source`, `fx_date` columns. [MAJOR-02]
5. **Resolve web authentication flow** — Document token handoff from Cognito → Next.js → browser → FastAPI. [MAJOR-03]
6. **Add source-adapters → domain-python dependency** — Missing from dependency graph. [MAJOR-04]
7. **Add organization_id to alert_deliveries** — Tenant scope must be explicit. [MAJOR-05]

### Before Week 3 (Identity/Catalog implementation)

8. **Standardize watch/catalog route naming** — Choose one namespace. [MINOR-01]
9. **Add health-check endpoints** — Required for ECS deployment. [NOTE-03]
10. **Create local development spec** — Required for developer onboarding. [NOTE-04]
11. **Decide Telegram mode** — Polling vs webhook. Recommend polling for MVP. [NOTE-05]

### Before Week 6 (Pipeline implementation)

12. **Fix worker TransientError handling** — Don't re-raise on transient errors. [MINOR-04]
13. **Decide pagination cursor strategy** — Use `published_at` not `score`. [MINOR-05]
14. **Decide raw_payload storage** — S3-key-first or JSONB threshold. [NOTE-01]

### Before Week 9 (Web implementation)

15. **Add timestamps to junction tables** — Consistency. [MINOR-02]
16. **Consider renaming valuation.listing_id → normalized_listing_id** — Clarity. [MINOR-03]

---

## Risks

### Risk 1: Undefined authentication bridge between Next.js and FastAPI

The web application architecture assumes browser components will call FastAPI directly, but the authentication token flow from Cognito callback through Next.js to the browser's JavaScript context is not designed. This is a **potential showstopper** for Week 9 web implementation. Must be resolved before any web API integration code is written.

### Risk 2: 12 backend modules for 25 references

The SRS defines 12 domain modules. For MVP scale, this module count may create excessive boilerplate (each module has domain/, application/, infrastructure/, api/ subdirectories — 48 directories minimum). Consider collapsing closely-related modules for MVP:
- `duplicates` → merge into `normalization` (duplicate detection is part of normalization)
- `feedback` → merge into `opportunities` (feedback is always on an opportunity)
- `operations` → could live in `sources` + `catalog` for MVP

### Risk 3: Staging environment requires real Cognito instance

Cognito cannot be realistically mocked locally. The staging environment needs a real Cognito user pool. This means either:
- Shared staging Cognito pool (potential test pollution)
- Per-branch Cognito pool (Terraform overhead, cost)

Neither is ideal. Consider what the "Development" environment actually provides for identity testing.

### Risk 4: Stripe billing before proven product-market fit

The roadmap places Stripe billing at Week 13, but the SRS MVP gate requires "Trial/paid/cancel/past-due entitlement states verified end-to-end." Building full billing integration before validating that dealers will pay is a scheduling risk. Consider decoupling billing from core feature development — implement entitlement gating as a feature flag initially, with Stripe integration as a parallel workstream that can be deferred without blocking feature work.

---

## Required ADR Updates

### ADR-0001 amendments needed

- **D4 (ULID keys):** Add note about ULID generation strategy (application-level vs database-level, library choice).
- **D6 (Idempotency):** Clarify that idempotency keys are the primary mechanism; database UNIQUE constraints are the enforcement layer.

### New ADRs needed

| ADR | Topic | When |
|-----|-------|------|
| ADR-0002 | WebSocket architecture (in-process vs dedicated) | Immediately |
| ADR-0003 | Web authentication flow (Cognito → Next.js → FastAPI) | Immediately |
| ADR-0004 | Module granularity (which modules to combine for MVP) | Before Week 1 |
| ADR-0005 | Telegram integration mode (polling vs webhook) | Before Week 6 |
| ADR-0006 | Cursor pagination implementation | Before Week 9 |

---

## Ready For Implementation?

**No — three blockers and five major issues must be resolved first.**

The architecture foundation is strong: the core decisions (modular monolith, PostgreSQL, Decimal, ULID, idempotency, tenant isolation, source adapter isolation, immutable records) are correct, consistent, and aligned with both the SRS and AGENTS.md. The monorepo structure, API conventions, database schema, worker topology, and security model are well-designed.

However, the following prevent implementation from starting:

1. **BLOCKER-01:** `alert_deliveries` schema bug — would fail migration
2. **BLOCKER-02:** Unresolved WebSocket architecture — affects scaling, deployment, cost
3. **MAJOR-03:** Undefined web auth flow — blocks all web feature work
4. **MAJOR-01:** Missing data_age in customer-visible estimates — AGENTS.md compliance gap

Once these are resolved and the recommended ADRs are created, the architecture is ready for Week 1 implementation (monorepo scaffolding, CI/CD pipeline, Terraform baseline).

**Recommended next step:** Resolve the four immediate issues above, create ADR-0002 and ADR-0003, then proceed with Week 1 implementation.
