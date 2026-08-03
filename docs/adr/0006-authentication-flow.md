# ADR-0006: Web Authentication Flow

**Status:** Accepted
**Date:** 2026-08-03
**Deciders:** Lead Software Architect
**Supersedes:** None
**Resolves:** Architecture Review MAJOR-03

---

## Context

The web application (Next.js App Router) and the backend API (FastAPI) are separate services. The SRS §8.1 states: "Use FastAPI as the system-of-record API. Next.js route handlers are limited to web-only edge concerns such as OIDC callbacks, secure cookie exchange and redirects."

This means browser-based client components must call FastAPI directly with a valid JWT. However, the OIDC Authorization Code flow with Amazon Cognito involves a server-side callback that exchanges the authorization code for tokens. These tokens are obtained on the Next.js server but must reach the browser's JavaScript context to be attached to API requests.

The current architecture documents do not specify the token handoff mechanism.

---

## Problem

### P1: Token must bridge server → browser → API

The OAuth 2.0 Authorization Code flow produces tokens on the server (Next.js route handler) but these tokens must be used by the browser (client components calling FastAPI). There are two paths:

1. **Server-side token injection:** Next.js proxies all API calls through server-side route handlers, injecting the token from the server session. Browser never sees the token.

2. **Client-side token storage:** Next.js passes tokens to the browser (via cookie or response body), and browser attaches them to API calls. Browser holds the token in memory.

### P2: SRS constrains Next.js role

The SRS §8.1 explicitly limits Next.js route handlers to "web-only edge concerns such as OIDC callbacks, secure cookie exchange and redirects." This precludes proxying all API traffic through Next.js (path 1 above), as that would make Next.js a full API proxy, not an edge concern.

### P3: JWT storage security in the browser

If the token reaches the browser, it must be stored securely:
- `localStorage` / `sessionStorage` — Vulnerable to XSS (any JavaScript on the page can read it).
- `httpOnly` cookie — Not accessible to JavaScript, so can't be attached to Authorization headers.
- In-memory JavaScript variable — Lost on page refresh/navigation.
- Non-httpOnly secure cookie — Readable by JavaScript but also by XSS.

---

## Decision

### D1: Hybrid token handoff via server-side session cookie → in-memory token

The authentication flow uses a server-side session cookie as a secure transport, then extracts the access token into browser memory for API calls.

**Complete flow:**

```
1. User visits /login
2. Redirected to Cognito hosted UI (OIDC Authorization Code + PKCE)
3. User authenticates with Cognito
4. Cognito redirects to /api/auth/callback?code=...  (Next.js route handler)
5. Next.js route handler:
   a. Exchanges code for tokens (access_token, refresh_token, id_token)
   b. Validates JWT signature against Cognito JWKS
   c. Extracts cognito:sub and verifies user exists in DB
   d. Creates server-side session (encrypted cookie with session ID)
   e. Stores tokens in Redis: session_id → { access_token, refresh_token, expires_at }
   f. Sets session cookie: httpOnly, Secure, SameSite=Lax, Path=/
   g. Redirects to /opportunities
6. On page load, client component calls GET /api/auth/session  (Next.js route handler)
   a. Reads session cookie
   b. Retrieves tokens from Redis
   c. Returns access_token in JSON response body
7. Client stores access_token in in-memory variable (React Context)
8. TanStack Query attaches Authorization: Bearer <access_token> to all FastAPI calls
9. When access_token expires (5 min before expiry):
   a. Client calls POST /api/auth/refresh  (Next.js route handler)
   b. Server uses refresh_token from Redis to get new access_token from Cognito
   c. Updates Redis with new tokens
   d. Returns new access_token
```

### D2: Redis as server-side token store

Tokens are stored in Redis with:
- Key: `session:{session_id}`
- Value: `{ access_token, refresh_token, id_token, expires_at, cognito_sub }`
- TTL: 7 days (aligns with Cognito refresh token validity)

**Rationale:**
- Redis is already deployed for caching, rate limiting, and WebSocket pub/sub.
- Enables server-side token management (refresh, revocation) without exposing tokens to the browser's persistent storage.
- Session revocation is instant: delete the Redis key.
- Survives Next.js server restarts (unlike in-memory storage).

### D3: Prefer Cognito refresh grant over custom refresh endpoint

Token refresh uses Cognito's standard OIDC refresh token grant. The Next.js route handler proxies the refresh call, keeping the Cognito client secret on the server.

### D4: Access token in browser memory only

The access token lives exclusively in a JavaScript variable (React Context). It is:
- Set on page load via `/api/auth/session`
- Refreshed before expiry via `/api/auth/refresh`
- Destroyed on logout / tab close

It is never written to `localStorage`, `sessionStorage`, or a non-httpOnly cookie.

---

## Architecture Diagram

```
┌──────────┐      ┌─────────────────────┐      ┌──────────┐      ┌──────────┐
│  Browser  │      │  Next.js (ECS)       │      │  Cognito  │      │  FastAPI  │
│ (SPA)    │      │  Route Handlers       │      │  (OIDC)   │      │  (API)    │
└────┬─────┘      └──────────┬──────────┘      └────┬─────┘      └────┬─────┘
     │                       │                      │                  │
     │  GET /login           │                      │                  │
     │──────────────────────►│                      │                  │
     │                       │──► redirect to       │                  │
     │                       │    Cognito UI        │                  │
     │◄── 302 Cognito ───────│                      │                  │
     │                       │                      │                  │
     │  GET Cognito UI       │                      │                  │
     │─────────────────────────────────────────────►│                  │
     │◄── Auth form ────────────────────────────────│                  │
     │                       │                      │                  │
     │  POST /api/auth/callback?code=...            │                  │
     │──────────────────────►│                      │                  │
     │                       │──► exchange code     │                  │
     │                       │    for tokens ──────►│                  │
     │                       │◄── tokens ───────────│                  │
     │                       │                      │                  │
     │                       │──► store in Redis    │                  │
     │                       │──► set session cookie│                  │
     │◄── 302 /opportunities─│                      │                  │
     │                       │                      │                  │
     │  GET /api/auth/session│                      │                  │
     │──────────────────────►│                      │                  │
     │                       │──► Redis get tokens  │                  │
     │◄── { access_token } ──│                      │                  │
     │                       │                      │                  │
     │  GET /api/v1/opportunities                   │                  │
     │  Authorization: Bearer <access_token>        │                  │
     │─────────────────────────────────────────────────────────────►│
     │◄── JSON response ────────────────────────────────────────────│
```

---

## Alternatives Considered

### Alternative A: Proxy all API calls through Next.js (rejected)

All `/api/v1/*` calls route through Next.js server-side route handlers that inject the token.

**Rejected because:** Violates SRS §8.1 limit on Next.js route handlers. Adds latency (double hop: browser → Next.js → FastAPI). Creates unnecessary load on Next.js servers. Makes Next.js a critical path dependency for all API traffic.

### Alternative B: Token in non-httpOnly cookie, read by JavaScript (rejected)

Store access token in a non-httpOnly secure cookie. JavaScript reads `document.cookie` and attaches to API calls.

**Rejected because:** Non-httpOnly cookies are readable by any JavaScript on the page, including injected scripts (XSS). This is a lower security posture than in-memory storage.

### Alternative C: BFF (Backend-for-Frontend) pattern with Next.js API routes (rejected)

Next.js serves as an API gateway with per-route handlers that call FastAPI.

**Rejected because:** Adds significant development overhead (duplicate API surface). SRS constrains Next.js to edge concerns. For MVP scale with a single API consumer (the web app), a BFF is over-engineering.

### Alternative D: Direct Cognito token to browser via implicit flow (rejected)

Use OIDC Implicit Flow where tokens are returned directly in the redirect URL fragment.

**Rejected because:** Implicit flow is deprecated by OAuth 2.1. Tokens in URL fragments are exposed to browser history, referrer headers, and JavaScript. Authorization Code + PKCE is the current best practice, especially for SPAs.

---

## Consequences

### Positive

- Access token never stored in persistent browser storage (XSS cannot steal it).
- Server-side session enables instant revocation (delete Redis key).
- Token refresh is transparent to the user (no re-login until refresh token expires).
- Next.js role is limited to OIDC callbacks and session management (SRS-compliant).
- All customer-facing API calls go directly to FastAPI (no proxy latency).

### Negative

- Redis is a runtime dependency for web authentication (mitigated: Redis already required for caching, rate limiting, WebSocket).
- Access token lost on page refresh (user re-fetches from `/api/auth/session` — a fast Redis lookup).
- Requires a dedicated `/api/auth/session` and `/api/auth/refresh` endpoint on Next.js.
- Slightly more complex than storing token in localStorage (but significantly more secure).

### Neutral

- The session cookie is httpOnly, so cookie-based CSRF is a concern. This is mitigated by:
  - SameSite=Lax cookie attribute (cookies not sent on cross-site requests)
  - The session endpoint returns JSON, not HTML (not useful to an attacker even if CSRF succeeds)
  - All state-changing API calls go directly to FastAPI with Bearer tokens (not cookie-based)

---

## Migration Impact

### New infrastructure (Week 1-2):
- Redis cluster must be accessible from Next.js ECS tasks (already accessible from FastAPI and workers — verify security group rules).

### New application code (Week 3-5, alongside Identity API):
- `apps/web/app/api/auth/callback/route.ts` — OIDC callback handler.
- `apps/web/app/api/auth/session/route.ts` — Session token retrieval.
- `apps/web/app/api/auth/refresh/route.ts` — Token refresh endpoint.
- `apps/web/app/api/auth/logout/route.ts` — Session destruction.
- `apps/web/lib/auth/` — Auth context, token management, React provider.

### New packages:
- None. Auth logic is Next.js-specific and lives in `apps/web/`.

### No database migration required (Redis, not PostgreSQL).

---

## Testing Implications

### Integration tests
- Full OIDC flow: login → callback → session → API call with Bearer token.
- Token refresh: simulated expired token → `/api/auth/refresh` → new token → API call succeeds.
- Logout: session destroyed → API call with old token fails with 401.
- Session expiry: Redis key TTL → `/api/auth/session` returns 401.

### Security tests
- XSS simulation: injected script cannot read access token from memory.
- CSRF: cross-site POST to `/api/auth/session` does not return tokens (SameSite=Lax).
- Token replay: expired access token rejected by FastAPI.
- Session fixation: session cookie regenerated on login.

### Contract tests
- `/api/auth/session` response schema matches expected `{ access_token, expires_at }`.
- FastAPI rejects requests with expired JWTs with correct error code (`UNAUTHORIZED`).

---

## References

- SRS §8.1: Next.js role constraints
- SRS §11.1: Identity baseline (OIDC, MFA, short tokens, PKCE)
- security-model.md §2: Identity and Authentication
- security-model.md §2.2: JWT validation rules
- Architecture Review: MAJOR-03, Risk 1
- AGENTS.md §12: Security and Privacy Rules
