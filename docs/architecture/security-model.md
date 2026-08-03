# ChronoArb — Security Model

**Document type:** Security architecture and compliance framework
**Source:** ChronoArb_MVP_SRS_v1.0 §11-12, AI-Agent Engineering Playbook §14
**Standards:** OWASP ASVS 5.0 Level 2
**Date:** 2026-08-03

---

## 1. Security Posture

ChronoArb handles commercially sensitive dealer acquisition behavior. The product must treat **tenant isolation as a critical security boundary**. Target: OWASP ASVS 5.0 Level 2 with heightened scrutiny on auth, authorization, webhooks, billing, and admin functions.

---

## 2. Identity and Authentication

### 2.1 Provider

Amazon Cognito (or approved OIDC-compliant equivalent) with:
- Authorization Code flow (web)
- PKCE flow (mobile)
- Short-lived access tokens (≤15 minutes) + refresh tokens
- MFA capability (required for admin roles)
- Session revocation on logout

### 2.2 JWT Validation

Every API request:
```
1. Extract Bearer token from Authorization header
2. Validate JWT signature against Cognito JWKS endpoint
3. Validate issuer (iss), audience (aud), expiry (exp)
4. Extract sub claim for user identity
5. Resolve organization membership from database
6. Reject if token invalid, expired, or user has no membership
```

### 2.3 Mobile

- OIDC with PKCE via system browser
- Tokens stored only in flutter_secure_storage (Keychain/Keystore)
- Biometric unlock does not replace server authentication
- No offline access after token/session expiry

---

## 3. Authorization Model

### 3.1 Role-Based Access Control (RBAC)

| Role | Scope | Key Permissions |
|------|-------|----------------|
| Owner | Organization | Full control, billing, member management |
| Admin | Organization | Manage members (non-owners), all dealer capabilities |
| Dealer | Organization | View opportunities, create alerts, record feedback/outcomes |
| Viewer | Organization | View opportunities, read-only |
| Platform Ops | Platform | Manage sources, catalog, jobs, admin functions |

### 3.2 Tenant Isolation

- Every tenant-scoped query includes explicit `organization_id`.
- Repository methods that access tenant data require mandatory `organization_id` parameter.
- `organization_id` is resolved server-side from validated JWT membership — never trusted from client input.
- Cross-tenant access must produce 404 (not 403) to prevent information leakage.
- Tenant-isolation tests run in CI and before every production release.

### 3.3 Deny-by-Default Principle

- All endpoints require authentication unless explicitly marked public (login, webhook).
- Authorization checks are server-side only. Client-side hiding is never access control.
- No security decisions based on client feature flags.

---

## 4. Transport Security

| Control | Implementation |
|---------|---------------|
| TLS | 1.2+ with modern cipher configuration on all endpoints |
| HSTS | Enabled on production web domains with appropriate max-age |
| Cookies | Secure, HttpOnly, SameSite=Strict for session cookies |
| Certificate management | AWS ACM with automatic rotation |

---

## 5. Data Protection

### 5.1 At Rest

| Data Store | Encryption |
|-----------|-----------|
| RDS PostgreSQL | AWS KMS encryption; automated backups encrypted |
| S3 (evidence, exports) | AWS KMS encryption; versioning for immutability |
| ElastiCache Redis/Valkey | Encryption at rest where supported |
| Mobile local storage | flutter_secure_storage + encrypted Drift |

### 5.2 In Transit

- All service-to-service communication over TLS
- RDS connections encrypted
- ElastiCache connections encrypted where supported
- SQS endpoints over HTTPS

---

## 6. Secrets Management

- All secrets stored in AWS Secrets Manager.
- No secrets in: source code, container images, environment variables, mobile bundles, logs, analytics, or test fixtures.
- Secret rotation automated where supported (RDS credentials).
- Developers use approved local secret tooling; never production secrets locally.

---

## 7. Webhook Security

| Control | Implementation |
|---------|---------------|
| Signature verification | HMAC-SHA256 signature validated on every webhook (Stripe) |
| Timestamp tolerance | Reject webhooks older than 5 minutes |
| Replay protection | Idempotency keys or processed event IDs |
| Rate limiting | Per-webhook-endpoint rate limits |

---

## 8. Input Validation and Output Encoding

- All API inputs validated through Pydantic v2 schemas with strict mode.
- Output encoded according to content type; HTML contexts use contextual escaping.
- Source data treated as untrusted: listing titles, descriptions, HTML, seller messages.
- No AI agent or runtime model treats source text as instructions, code, config, URLs, or authorization.

---

## 9. SSRF Prevention

- Outbound source domains are allowlisted per adapter.
- Workers never fetch customer-supplied arbitrary URLs.
- Hardened egress policy at network level.
- Source URLs validated against allowlist before any outbound request.

---

## 10. Admin Security

- MFA enforced for all admin/operations roles.
- Least privilege IAM roles; shared cloud credentials prohibited.
- All privileged actions create immutable audit events.
- Time-limited elevated access where applicable.
- Production access uses SSO.

---

## 11. Supply Chain Security

- All dependencies pinned to tested patch versions in lock files.
- Automated dependency updates require CI + staging validation.
- SBOM generated for each release.
- Container images signed and scanned (Trivy).
- Vulnerability scanning: SAST (Semgrep), dependency (pip-audit/Trivy), infrastructure (Terraform policy checks).
- Patch SLA for critical vulnerabilities.

---

## 12. Incident Response

- Severity matrix: SEV1 (critical) through SEV4 (informational).
- On-call ownership defined per service area.
- Containment runbook: source pause, alert kill switch, credential revoke, worker scale-down.
- Customer notification process for data breaches.
- Post-incident: root cause analysis, prevention owner, test/runbook updates.

---

## 13. Privacy

| Data Category | Treatment |
|--------------|-----------|
| User identity | Minimum fields; access/correction/deletion workflow |
| Dealer strategies/outcomes | Private tenant data; restricted staff access; not sold |
| Telegram/device IDs | Delivery only; revoke on unlink; minimize retention |
| Location | Organization/source geography; no continuous GPS |
| Telemetry | Pseudonymous IDs; scrub tokens, raw text, financial details |
| Source seller data | Minimize, retain/display only as permitted |

---

## 14. Fraud and Abuse Controls

| Control | Implementation |
|---------|---------------|
| Rate limiting | Account creation, invitations, source-link clicks, API reads, notification tests |
| Credential sharing detection | Anomalous access patterns without blocking legitimate teams |
| Aggregate data export | Protected behind enterprise entitlement and audit |
| Suspicious listing reporting | Action available without claiming authentication capability |
| Arbitrary URL fetch | Blocked in MVP; allowlisted domains only |

---

## 15. Source Compliance

Every source requires before production enablement:
- [ ] Recorded legal/business review
- [ ] Documented approved access mode
- [ ] Permitted fields, rate limits, display/retention constraints
- [ ] Owner contact for takedown/complaints

Operational controls:
- Sources can be paused/disabled without deployment.
- Separate credentials per source; never use personal sessions.
- Re-review when terms, APIs, structure, auth, geography, or commercial use change.
- Takedown/contact process and evidence preservation documented.

---

## 16. Audit Events

Every privileged action creates an immutable audit event:

| Action | Resource | Details |
|--------|----------|---------|
| member.invited | Organization | Who invited whom, role |
| member.role_changed | Membership | From role → To role, by whom |
| member.removed | Membership | By whom |
| source.enabled | Source | Which source, by whom |
| source.disabled | Source | Which source, reason |
| job.replayed | Job | Job ID, range, by whom |
| dlq.replayed | DLQ message | Message ID, by whom |
| flag.updated | Feature flag | Key, old/new value, by whom |
| billing.* | Subscription | All billing state changes |

Audit events include: `organization_id`, `user_id`, `action`, `resource_type`, `resource_id`, `details`, `trace_id`, `client_ip`, `created_at`.
