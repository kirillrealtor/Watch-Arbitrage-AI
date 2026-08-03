# ChronoArb — Development Roadmap

**Document type:** MVP build plan and workstream sequencing
**Source:** ChronoArb_MVP_SRS_v1.0 §16, AI-Agent Engineering Playbook §18
**Date:** 2026-08-03

---

## 1. MVP Target

| Gate | Criteria |
|------|----------|
| Scope | 25 active supported references, 3 production-approved sources |
| Quality | ≥98% reference precision; <15% hard false positives; ≥95% duplicate precision |
| Timeliness | p95 source-to-alert <10 min for high-priority sources; notification dispatch p95 <30 s |
| Availability | Customer API/web staging soak meets 99.5% target design |
| Security | No critical/high release-blocking findings; tenant-isolation suite passes |
| Clients | Web + signed iOS/Android release candidates complete critical journeys |
| Billing | Trial/paid/cancel/past-due entitlement states verified end-to-end |
| Operations | Source pause, alert kill switch, DLQ replay, restore procedures tested |
| Commercial | ≥10 design partners used system; paid conversion hypothesis documented |

## 2. Team Assumptions

Cross-functional team: ~2 backend/data engineers, 1 web engineer, 1 Flutter engineer, 1 product designer, fractional QA/security/DevOps, active dealer design partners.

**Risk:** Source contract/access delays can dominate the schedule and must be treated as a separate commercial workstream.

---

## 3. Workstreams and Dependencies

```
Foundation ──► Domain/Data ──► Source Pipeline ──► Intelligence
                 │                                      │
                 └──────────────┬───────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
              Notifications    Web       Mobile
                    │           │           │
                    └───────────┼───────────┘
                                │
                          Commercial
                                │
                           Hardening
```

### 3.1 Workstream Details

| Workstream | Early Deliverables | Dependency |
|-----------|-------------------|------------|
| Foundation | Monorepo, pinned tools, CI, Terraform baseline, identity skeleton | None |
| Domain/Data | Catalog, money/value objects, tenant policies, schema, migrations | Foundation |
| Source Pipeline | Adapter protocol, first approved adapter, raw snapshots, queues, admin trace | Domain/Data |
| Intelligence | Normalization, duplicates, valuation, opportunity publication | Source Pipeline |
| Notifications | Rule matching, Telegram, push, idempotency, delivery logs | Intelligence + Identity |
| Web | Onboarding, opportunity feed/detail, settings, activity, admin | API contracts |
| Mobile | Auth, feed/detail, push/deep links, offline feedback | API contracts + Notifications |
| Commercial | Stripe billing, entitlements, portal, audit | Identity + Web |
| Hardening | Second/third sources, model tuning, performance, security, accessibility, runbooks | All critical paths |

---

## 4. 16-Week Build Plan

### Weeks 1-2: Architecture Baseline

| Task | Outcome |
|------|---------|
| Monorepo scaffolding | pnpm workspaces, Turborepo/Nx, shared tsconfig/pyproject |
| CI/CD pipeline | GitHub Actions: lint, type-check, test, build, scan |
| Terraform baseline | VPC, RDS, ElastiCache, S3, ECR, IAM roles |
| Identity skeleton | Cognito user pool, JWT validation, basic user/membership tables |
| Source/legal inventory | Identify 3 approved sources, begin access agreements |
| UX flows | Wireframes for opportunity feed, detail, alert builder |
| Catalog schema | Brands, references, variants, aliases tables |

### Weeks 3-5: Identity, Catalog, First Source

| Task | Outcome |
|------|---------|
| Identity API | User/organization CRUD, invitations, RBAC middleware |
| Canonical catalog | 25 references with attributes, aliases, source mappings |
| Source adapter #1 | Discovery, fetch, parse, fixtures, health assertions |
| Raw snapshots | Immutable evidence storage with lineage |
| Operations trace | Trace ID propagation across pipeline stages |
| Queue infrastructure | SQS queues + DLQs, worker skeleton |

### Weeks 6-8: Intelligence Pipeline

| Task | Outcome |
|------|---------|
| Normalization engine | Reference matching, attribute extraction, confidence scoring |
| Duplicate detection | Candidate generation, similarity scoring, representative selection |
| Cost model | Fee assumptions, tax/duty tables, shipping estimates |
| Valuation v1 | Comparable selection, adjustments, cost waterfall, bands |
| Opportunity publication | Scoring, lifecycle, material versions, explanations |
| Alert matching | Rule engine, cooldowns, idempotent delivery records |
| Telegram notification | Bot integration, message delivery, link-back |

### Weeks 9-10: Web Dashboard

| Task | Outcome |
|------|---------|
| Auth + onboarding | Login, organization setup, assumption configuration |
| Opportunity feed | Ranked feed with filters, sorting, pagination |
| Opportunity detail | Cost waterfall, comps, risks, history, feedback actions |
| Alerts UI | Rule builder, channel configuration, test notification |
| Activity feed | Team decisions and outcomes |
| Settings | Organization, integrations, billing pages |
| Admin console | Sources, jobs, unmatched, duplicates, flags |
| Accessibility | WCAG 2.2 AA conformance pass |

### Weeks 11-12: Mobile Application

| Task | Outcome |
|------|---------|
| Auth + PKCE | Secure OIDC flow with token storage |
| Opportunity feed | Riverpod-driven feed with offline cache |
| Opportunity detail | Cost breakdown, progressive disclosure on small screens |
| Push notifications | FCM integration, deep links, foreground/background handling |
| Offline feedback | Queue with idempotency, sync on connectivity |
| Settings | Integrations, notification preferences |
| Accessibility | VoiceOver/TalkBack, dynamic text |

### Weeks 13: Billing and Entitlements

| Task | Outcome |
|------|---------|
| Stripe integration | Customer mapping, subscription lifecycle |
| Checkout + Portal | Hosted Stripe UI for payment/cancel |
| Webhook handler | Signature verification, idempotent state updates |
| Entitlement gates | Feature access based on subscription status |
| Audit trail | Billing event logging |
| Mobile billing | App store companion approach, policy review |

### Weeks 14: Source #2, #3 and Model Tuning

| Task | Outcome |
|------|---------|
| Source adapter #2 | Same adapter contract, new source-specific parser |
| Source adapter #3 | Third production source |
| Valuation calibration | Per-reference accuracy analysis, adjustment table tuning |
| False positive reduction | Manual review feedback loop, model improvements |
| Performance optimization | Query plan review, cache strategy, worker tuning |

### Weeks 15: Closed Beta Hardening

| Task | Outcome |
|------|---------|
| Security review | SAST, DAST, dependency audit, tenant isolation tests |
| Accessibility audit | Automated + manual review, remediation |
| Performance testing | Load tests for feed, API, worker throughput |
| Runbooks completed | All 8 mandatory runbooks written and tested |
| Kill switch drills | Source pause, alert suppression, DLQ replay |
| Restore drill | RDS point-in-time recovery exercise |
| Store submission | iOS and Android app store review process |

### Weeks 16: Release Candidate

| Task | Outcome |
|------|---------|
| Final acceptance | All MVP gate criteria verified |
| Design partner launch | ≥10 dealers active on platform |
| Monitoring dashboards | All required signals instrumented |
| Launch documentation | Support process, escalation paths, SLAs |
| Go-live | Production deployment with blue/green strategy |

---

## 5. Contract-First Sequencing

To maximize parallel work, follow this sequence:

1. **Define contracts first:** Domain types, API schemas, event envelopes, error codes.
2. **Create contract tests:** Source adapter fixtures, OpenAPI tests, generated clients.
3. **Implement backend services:** Against contract tests.
4. **Implement web + mobile in parallel:** Against generated clients and stable mocks.
5. **Integrate notifications + offline behavior.**
6. **Run end-to-end, security, accessibility, performance acceptance.**
7. **Enable through feature flags** and observe design partners.

---

## 6. Critical Path Protection

**Do not assign all effort to visible UI while these are unresolved:**

- Data contracts and API schemas
- Source approval and access agreements
- Identity and tenant isolation
- Database schema and migrations
- Pipeline idempotency

Web and mobile can parallelize effectively only after stable contracts and representative fixtures exist.

---

## 7. Change Freeze Rules

| Period | Allowed Changes |
|--------|----------------|
| Normal development | Approved task work with standard gates |
| Beta hardening (Week 15) | Block architecture churn; allow defects, quality, security, observability, essential scope |
| Release candidate (Week 16) | Only release blockers with explicit owner and rollback plan |
| Incident | Smallest containment/fix; document bypassed gates; restore after |

---

## 8. Milestones by Week

| Week | Milestone |
|------|-----------|
| 2 | CI green, infrastructure bootstrapped, identity skeleton |
| 5 | First source producing raw snapshots, catalog populated |
| 8 | First opportunity alerts delivered via Telegram |
| 10 | Web dashboard complete, dealers can view and act on opportunities |
| 12 | Mobile app complete, push notifications functional |
| 13 | Billing end-to-end, trial/paid entitlements verified |
| 14 | Three sources operational, model tuned |
| 15 | Security and accessibility signed off, runbooks tested |
| 16 | MVP release candidate, design partners onboarded |
