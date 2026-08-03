# ADR-0003: Realtime Communication Strategy

**Status:** Accepted
**Date:** 2026-08-03
**Deciders:** Lead Software Architect
**Supersedes:** None
**Resolves:** Architecture Review BLOCKER-02

---

## Context

The SRS requires real-time updates for the opportunity feed (§8.3: "Authenticated WebSocket updates invalidate or patch query cache; fallback polling with jitter"). The API design document defines a WebSocket endpoint at `wss://api.chronoarb.com/ws?token=<JWT>` with four event types. The NFR-PERF-002 states: "WebSocket foreground updates shall reach connected clients within 5 seconds of committed opportunity publication under normal conditions."

Two unresolved architectural questions:
1. Does the WebSocket server run in-process with FastAPI or as a dedicated service?
2. How do worker processes (which publish opportunities) deliver events to WebSocket-connected clients?

---

## Problem

### P1: In-process vs dedicated service trade-offs

| Dimension | In-process (FastAPI) | Dedicated service |
|-----------|---------------------|-------------------|
| Deployment | One service | Two services |
| Scaling | Sticky sessions needed for multi-instance | Independent scaling |
| Worker → client path | Redis pub/sub required for cross-instance fanout | Direct Redis pub/sub or gRPC to service |
| Auth | Reuses FastAPI JWT validation | Duplicates or proxies auth |
| MVP complexity | Low | High |
| Connection limit | Bounded by FastAPI event loop + memory | Scales independently |
| SRS NFR compliance | Meets 5-second latency for MVP volume | Meets with headroom |

### P2: Worker-to-WebSocket communication path

When a valuation worker creates an opportunity, it runs in a separate ECS task with no direct network path to WebSocket-connected clients. An intermediary is required.

---

## Decision

### D1: In-process WebSocket with Redis pub/sub fanout for MVP

The WebSocket server shall run within the FastAPI process. Worker processes shall publish events to Redis pub/sub channels. The FastAPI process shall subscribe to these channels and forward events to connected WebSocket clients.

**Architecture:**

```
Worker (ECS)                    FastAPI (ECS)                  Browser
    │                               │                            │
    │  opportunity.published        │                            │
    │──► Redis PUBLISH ────────────►│  Redis SUBSCRIBE            │
    │    channel: org:{org_id}      │                            │
    │                               │  Filter by org_id          │
    │                               │  Resolve connected clients  │
    │                               │──► WebSocket send ─────────►│
```

### D2: Organization-scoped Redis channels

Events are published to `org:{organization_id}:opportunities` channels. Each FastAPI instance subscribes to channels for organizations with active connections. This ensures a worker event for org A is never forwarded to a browser connected for org B.

### D3: Fallback polling with jitter for resilience

All WebSocket clients implement a fallback polling mechanism using TanStack Query's `refetchInterval` with jitter. If the WebSocket disconnects or the 5-second delivery window is missed, polling covers the gap.

Polling interval: 30 seconds with ±5 second jitter.

### D4: WebSocket authentication via connection-time JWT validation

The WebSocket upgrade request carries a JWT as a query parameter (`?token=<JWT>`). The FastAPI WebSocket endpoint validates the JWT before accepting the connection. The token is validated once at connection time; subsequent messages are trusted within the connection scope.

**Security note:** JWT in URL query strings may be logged by ALB/CloudFront access logs. Mitigations:
- Use short-lived access tokens (≤15 minutes already established in security-model.md)
- Configure ALB/CloudFront to redact query strings from access logs for the `/ws` path
- Accept JWT via `Sec-WebSocket-Protocol` header as an alternative for clients that support it

---

## Alternatives Considered

### Alternative A: Dedicated WebSocket service (rejected for MVP)

A separate ECS service handling WebSocket connections, with workers publishing directly to it.

**Rejected because:**
- Adds infrastructure complexity (separate ECS service, separate scaling, separate deployment).
- Duplicates JWT validation logic.
- For MVP with ~10 design partners and <50 concurrent connections, the in-process approach is sufficient.
- Can be extracted to a dedicated service later without API contract changes.

**Migration path:** If connection counts grow beyond FastAPI's capacity, the WebSocket logic can be extracted into a dedicated service using the same Redis pub/sub pattern. The API contract (event types, channel naming) remains unchanged. Only the connection endpoint URL changes, with a DNS cutover.

### Alternative B: Server-Sent Events (SSE) instead of WebSocket (rejected)

**Rejected because:**
- SSE is unidirectional (server → client). Opportunities also need client → server actions (e.g., feedback), but these go through REST, so SSE could work.
- SRS explicitly specifies WebSocket (§8.3).
- WebSocket has broader client library support.
- SSE connection limits in HTTP/1.1 (6 per domain) are not a concern at MVP scale but would constrain future growth.

### Alternative C: SQS-backed polling only, no WebSocket (rejected)

**Rejected because:**
- NFR-PERF-002 requires ≤5-second delivery to connected clients.
- Polling at ≤5-second intervals generates excessive API load even at moderate scale.
- SRS explicitly requires WebSocket.

---

## Consequences

### Positive

- Single service to deploy and monitor for MVP.
- Redis pub/sub provides clean worker-to-API event delivery.
- Organization-scoped channels enforce tenant isolation at the messaging layer.
- Fallback polling ensures resilience during WebSocket disconnections.
- Migration path to dedicated WebSocket service exists without contract changes.

### Negative

- FastAPI process memory grows with connected clients (mitigated: expected <50 concurrent connections at MVP).
- JWT in URL query string is a known security consideration (mitigated: log redaction, short-lived tokens).
- Horizontal scaling requires ALB sticky sessions for WebSocket connections.
- Redis pub/sub adds a runtime dependency on Redis (already present for caching, so no new infrastructure).

### Neutral

- The `Sec-WebSocket-Protocol` header alternative for JWT delivery requires client-side support that may not be available in all browser WebSocket implementations.

---

## Migration Impact

### Infrastructure (Terraform, Week 1-2):
- No additional ECS service needed for MVP.
- ALB must support WebSocket upgrades (standard ALB behavior, no special config).
- ALB access log query string redaction for `/ws` path pattern.
- Redis pub/sub enabled on existing ElastiCache cluster.

### Application (Week 9-10, alongside web dashboard):
- `apps/api/` — New WebSocket endpoint module with connection manager.
- `apps/worker/` — Redis publisher utility for events.
- `packages/domain-python/` — Event type definitions (already defined in events.py).

### No database migration required.

---

## Testing Implications

### Integration tests
- WebSocket connection upgrade with valid JWT → 101 Switching Protocols.
- WebSocket connection with invalid/expired JWT → 401/403, connection refused.
- Worker publishes event → event received on WebSocket within 5 seconds (measured in integration test).
- Event for org A is not delivered to WebSocket connection for org B.

### Performance tests
- Load test with expected MVP concurrency (50 concurrent WebSocket connections).
- Measure event delivery latency: worker publish → WebSocket receive.
- Verify that 50 WebSocket connections do not measurably increase API latency for REST requests.

### Contract tests
- Event schema validation: published events match the defined event types.
- Connected client receives only events with correct organization_id.
- Event types (`opportunity.published`, `opportunity.updated`, `opportunity.expired`, `alert.delivered`) are exhaustive.

### Fallback tests
- Kill WebSocket connection → client falls back to polling within 35 seconds (30s interval + 5s jitter).
- Re-establish WebSocket → client switches back from polling.

---

## References

- SRS §8.3: Web real-time updates requirement
- SRS §8.5: WebSocket fallback polling requirement
- NFR-PERF-002: 5-second WebSocket delivery target
- api-design.md §3.10: WebSocket endpoint and event types
- worker-design.md §7: Concurrency and scaling
- system-design.md §1: Architecture overview diagram
- security-model.md §2.2: JWT validation
- Architecture Review: BLOCKER-02
