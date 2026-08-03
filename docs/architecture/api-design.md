# ChronoArb — API Design

**Document type:** REST API contract and design
**Source:** ChronoArb_MVP_SRS_v1.0 §10, AI-Agent Engineering Playbook §11, §13
**Date:** 2026-08-03

---

## 1. API Conventions

| Convention | Rule |
|-----------|------|
| URL prefix | `/api/v1/` |
| Case style | `snake_case` for all JSON keys |
| Timestamps | RFC 3339 UTC (`2026-08-02T16:42:19Z`) |
| Money | String representation, e.g. `"11150.00"` with explicit `currency` field (ISO 4217) |
| Pagination | Opaque cursor-based for mutable feeds; `next_cursor` in response |
| Errors | Stable envelope: `{ error_code, message, field_errors, trace_id, retryable }` |
| Idempotency | `Idempotency-Key` header on retryable write endpoints |
| Content-Type | `application/json` |
| Authorization | `Authorization: Bearer <JWT>` |

## 2. Response Envelope

### Success

```json
{
  "data": { ... },
  "meta": {
    "trace_id": "trc_01J...",
    "next_cursor": "cur_01J...",
    "has_more": true
  }
}
```

### Error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "One or more fields are invalid.",
    "field_errors": {
      "email": ["must be a valid email address"]
    },
    "trace_id": "trc_01J...",
    "retryable": false
  }
}
```

### Error Codes

| Code | HTTP Status | Retryable |
|------|-------------|-----------|
| VALIDATION_ERROR | 422 | No |
| UNAUTHORIZED | 401 | No |
| FORBIDDEN | 403 | No |
| NOT_FOUND | 404 | No |
| CONFLICT | 409 | No (idempotent retry returns original) |
| RATE_LIMITED | 429 | Yes |
| INTERNAL_ERROR | 500 | Yes |
| SERVICE_UNAVAILABLE | 503 | Yes |

---

## 3. Operational Endpoints

Operational endpoints serve infrastructure and deployment needs — load balancer health checks, ECS task readiness probes, and monitoring systems. They are not part of the customer-facing API contract.

### 3.1 Envelope Distinction

Operational endpoints use a **simplified response format** that omits the `meta` wrapper. The `trace_id` is embedded directly in the response data:

```
GET /health
→ { "data": { "status": "ok", "trace_id": "trc_01J..." } }

GET /ready
→ { "data": { "status": "ok", "database": "connected", "trace_id": "trc_01J..." } }
```

This is intentional: operational endpoints are consumed by machines (ALB target group health checks, ECS health checks, monitoring agents) that do not parse the full API envelope. Including a `meta` wrapper would break every standard health-check consumer.

### 3.2 Customer vs Operational Envelope

| Concern | Customer API (`/api/v1/*`) | Operational (`/health`, `/ready`) |
|---------|---------------------------|-----------------------------------|
| Envelope | `{ "data": ..., "meta": { "trace_id": "..." } }` | `{ "data": { ..., "trace_id": "..." } }` |
| Authentication | Required (JWT) | None |
| Rate limiting | Applied | Excluded |
| OpenAPI schema | Included | Excluded (`include_in_schema=False`) |
| Error format | `{ "error": { "code": "..." } }` | Standard HTTP status codes |
| Consumers | Browser, mobile app | Load balancer, ECS, monitoring |

### 3.3 Endpoint Listing

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness probe — returns 200 if the process is running |
| GET | `/ready` | Readiness probe — returns 200 if the process can serve traffic (database reachable) |

---

## 4. API Route Map

### 4.1 Identity (`/api/v1/identity`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/identity/me` | Current user profile and memberships |
| POST | `/identity/organizations` | Create organization |
| GET | `/identity/organizations/{org_id}` | Organization details |
| PATCH | `/identity/organizations/{org_id}` | Update settings |
| POST | `/identity/organizations/{org_id}/invitations` | Invite member |
| GET | `/identity/organizations/{org_id}/members` | List members |
| PATCH | `/identity/organizations/{org_id}/members/{user_id}` | Change role |
| DELETE | `/identity/organizations/{org_id}/members/{user_id}` | Remove member |

### 4.2 Catalog (`/api/v1/catalog`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/catalog/references` | List canonical references (paginated, filterable) |
| GET | `/catalog/references/{ref_id}` | Reference detail with market stats |
| GET | `/catalog/references/{ref_id}/price-history` | Price history |
| GET | `/catalog/brands` | List brands |
| GET | `/catalog/watch-lists` | User's watch lists |
| POST | `/catalog/watch-lists` | Create watch list |
| PUT | `/catalog/watch-lists/{id}` | Update watch list |
| DELETE | `/catalog/watch-lists/{id}` | Delete watch list |

### 4.3 Opportunities (`/api/v1/opportunities`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/opportunities` | Ranked opportunity feed (paginated, filterable) |
| GET | `/opportunities/{opp_id}` | Full deal analysis with cost waterfall, comps, risks |
| POST | `/opportunities/{opp_id}/feedback` | Record decision (PURCHASED/CONTACTED/DISMISSED) |
| GET | `/opportunities/{opp_id}/history` | Material version history |
| POST | `/opportunities/{opp_id}/trade-outcome` | Record realized trade outcome |

### 4.4 Watches (`/api/v1/watches`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/watches/{ref_id}/market` | Market detail: valuation bands, comps, price history |

### 4.5 Alerts (`/api/v1/alerts`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/alerts/rules` | List alert rules |
| POST | `/alerts/rules` | Create alert rule |
| GET | `/alerts/rules/{rule_id}` | Alert rule detail |
| PUT | `/alerts/rules/{rule_id}` | Update alert rule |
| DELETE | `/alerts/rules/{rule_id}` | Delete alert rule |
| POST | `/alerts/rules/{rule_id}/test` | Send test notification |
| GET | `/alerts/deliveries` | Alert delivery history |

### 4.6 Activity (`/api/v1/activity`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/activity` | Team activity feed (decisions, outcomes) |
| GET | `/activity/outcomes` | Recorded trade outcomes |

### 4.7 Settings (`/api/v1/settings`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/settings/organization` | Organization assumptions (currency, tz, default fees) |
| PATCH | `/settings/organization` | Update organization assumptions |
| GET | `/settings/integrations` | Telegram/push connection status |
| POST | `/settings/integrations/telegram` | Link Telegram |
| DELETE | `/settings/integrations/telegram` | Unlink Telegram |
| POST | `/settings/integrations/push` | Register device token |
| DELETE | `/settings/integrations/push/{token}` | Unregister device |

### 4.8 Billing (`/api/v1/billing`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/billing/subscription` | Current subscription status |
| POST | `/billing/checkout` | Create Stripe Checkout session |
| POST | `/billing/portal` | Create Stripe Customer Portal session |
| POST | `/billing/webhook` | Stripe webhook (unauthenticated, signature-verified) |

### 4.9 Operations (`/api/v1/admin`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin/sources` | List sources with health |
| PATCH | `/admin/sources/{source_id}` | Enable/disable/pause source |
| GET | `/admin/jobs` | Job list with status |
| POST | `/admin/jobs/{job_id}/replay` | Replay job |
| GET | `/admin/dlq` | DLQ message list |
| POST | `/admin/dlq/{msg_id}/replay` | Replay DLQ message |
| DELETE | `/admin/dlq/{msg_id}` | Discard DLQ message |
| GET | `/admin/flags` | List feature flags |
| PATCH | `/admin/flags/{flag_id}` | Update feature flag |
| GET | `/admin/unmatched` | Unmatched/ambiguous listings |
| POST | `/admin/unmatched/{listing_id}/resolve` | Resolve unmatched listing |
| GET | `/admin/duplicates` | Duplicate review queue |
| GET | `/admin/audit` | Audit event log |

### 4.10 WebSocket

| Endpoint | Purpose |
|----------|---------|
| `wss://api.chronoarb.com/ws?token=<JWT>` | Authenticated real-time updates |

**Events:**
- `opportunity.published` — New opportunity available
- `opportunity.updated` — Material version change
- `opportunity.expired` — Opportunity no longer active
- `alert.delivered` — Notification delivery confirmation

---

## 5. Pagination

Cursor-based pagination for all mutable feeds:

```json
// Request
GET /api/v1/opportunities?cursor=cur_01J...&limit=50&sort=score_desc

// Response
{
  "data": [ ... ],
  "meta": {
    "trace_id": "trc_01J...",
    "next_cursor": "cur_01JABC...",
    "has_more": true
  }
}
```

---

## 6. Idempotency

Retryable write endpoints accept `Idempotency-Key` header:

```
POST /api/v1/opportunities/opp_01J.../feedback
Idempotency-Key: idem_01JDEF...

// If retried with same key, returns 200 with original result.
// If different payload with same key, returns 422.
```

---

## 7. OpenAPI Generation

- OpenAPI spec generated from Pydantic v2 models using FastAPI's built-in support.
- Spec committed to `docs/api/openapi.yaml`.
- Breaking change detection runs in CI; unapproved breaking changes block merge.
- TypeScript client regenerated via `openapi-typescript` or equivalent.
- Dart client regenerated via `openapi-generator` or equivalent.
- Generated clients committed to `packages/api-client-ts/` and `packages/api-client-dart/`.

---

## 8. Authorization Model

Every protected endpoint requires:
1. Valid JWT (validated against Cognito JWKS)
2. Active membership in the organization identified by the request context
3. Role meeting the minimum required for the endpoint

Authorization is resolved from the JWT claims, never from client-supplied organization parameters. The `organization_id` in route paths is validated against the authenticated user's memberships.
