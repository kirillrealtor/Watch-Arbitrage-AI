# ChronoArb — System Design

**Document type:** Architecture overview
**Source:** ChronoArb_MVP_SRS_v1.0 §7, AI-Agent Engineering Playbook §11-13
**Date:** 2026-08-03

---

## 1. Architecture Overview

ChronoArb follows a **modular monolith with async workers** pattern. The customer-facing API is a single FastAPI service. Long-running ingestion, normalization, valuation, matching, and notification work execute in separate worker processes driven by SQS queues.

```
                                ┌──────────────┐
                                │   CloudFront  │
                                │   + WAF + ALB │
                                └──────┬───────┘
                                       │
              ┌────────────────────────┼─────────────────────────┐
              │                        │                         │
    ┌─────────▼────────┐   ┌──────────▼──────────┐   ┌─────────▼─────────┐
    │   Next.js (ECS)  │   │  FastAPI (ECS)      │   │  Mobile clients    │
    │   web dashboard  │   │  /api/v1/*          │   │  (iOS/Android)     │
    └────────┬─────────┘   └──────────┬──────────┘   └─────────┬─────────┘
             │                        │                         │
             │              ┌─────────▼─────────┐               │
             │              │   Cognito (OIDC)  │               │
             │              └───────────────────┘               │
             │                        │                         │
             └────────────────────────┼─────────────────────────┘
                                      │
    ┌─────────────────────────────────┼──────────────────────────────────┐
    │                                 │                                  │
    │  ┌──────────┐   ┌───────────────▼──────────────┐   ┌───────────┐  │
    │  │   SQS    │◄──┤       API / Workers          │──►│  Stripe   │  │
    │  │  Queues  │   │  (ECS Fargate tasks)          │   │  Billing  │  │
    │  └────┬─────┘   └───────────────┬──────────────┘   └───────────┘  │
    │       │                         │                                  │
    │       │    ┌────────────────────┼─────────────────────┐            │
    │       │    │                    │                     │            │
    │  ┌────▼────▼──┐   ┌────────────▼──────────┐   ┌─────▼─────────┐  │
    │  │  Workers   │   │   RDS PostgreSQL 18   │   │  ElastiCache  │  │
    │  │  (ECS)     │   │   (system of record)  │   │  Redis/Valkey │  │
    │  └────────────┘   └───────────────────────┘   └───────────────┘  │
    │                                                                   │
    │  ┌────────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
    │  │  S3        │   │  FCM (push)  │   │  OpenTelemetry →          │ │
    │  │  Evidence  │   │  Telegram    │   │  CloudWatch / Sentry     │ │
    │  └────────────┘   └──────────────┘   └──────────────────────────┘ │
    └───────────────────────────────────────────────────────────────────┘
```

## 2. Processing Flow

The core data pipeline (SRS §7.4):

```
Source Discovery ──► Fetch ──► Parse ──► Normalize ──► Deduplicate
                                                              │
                                                              ▼
Notification ◄── Match Alerts ◄── Publish Opportunity ◄── Valuate
    │                                                          │
    ▼                                                          │
  Dealer ──► View Opportunity ──► Record Feedback ──► Learn
```

Each stage is a separate SQS queue + worker process. Every record carries trace/correlation IDs from source to notification.

## 3. Request Flow (Customer-Facing)

```
Browser/Mobile
    │
    ▼
CloudFront + WAF + ALB
    │
    ▼
FastAPI (ECS Fargate)
    ├── Extract JWT → validate with Cognito JWKS
    ├── Resolve organization + role from membership
    ├── Validate request schema (Pydantic)
    ├── Call application service
    │   ├── Authorization check (org-scoped)
    │   ├── Domain policy invocation
    │   └── Repository call (tenant-scoped SQL)
    ├── Map result to Pydantic response schema
    └── Return JSON with trace_id
```

## 4. Queue Topology

| Queue | Producer | Consumer | Failure |
|-------|----------|----------|---------|
| source-discovery | EventBridge / admin replay | Discovery workers | Retry, then DLQ + source pause threshold |
| source-fetch | Discovery workers | Fetch workers | Source-specific retry/backoff |
| normalize-listing | Fetch/parser workers | Normalization workers | Quarantine invalid/low-confidence |
| value-listing | Normalizer / price change event | Valuation workers | Retry transient; flag model/config errors |
| match-alerts | Opportunity service | Alert matcher | Idempotent by opportunity material version |
| send-notification | Alert matcher | Channel workers (Telegram, FCM) | Provider retry, permanent-failure suppression + DLQ |
| analytics-events | API/workers | Analytics sink | Non-blocking; monitored loss |

## 5. Deployment Model

```
┌─────────────────────────────────────────┐
│  GitHub Actions CI Pipeline              │
│  Lint → Type-check → Test → Build → Scan │
└──────────────────┬──────────────────────┘
                   │
          ┌────────▼────────┐
          │  Staging (ECS)  │  ← Auto-deploy on merge to main
          │  Migration      │
          │  E2E + Security │
          └────────┬────────┘
                   │ Manual approval
          ┌────────▼────────┐
          │  Production     │  ← Blue/green or rolling deploy
          │  Smoke checks   │
          │  Auto-rollback  │
          └─────────────────┘
```

## 6. Environment Strategy

| Environment | Purpose | Data |
|-------------|---------|------|
| Local | Developer workstation with Docker Compose | Synthetic/test fixtures only |
| Development | Shared integration and feature testing | Synthetic + approved sandbox data |
| Staging | Release candidate, performance/security validation | Sanitized or separately collected |
| Production | Customer service, approved source jobs | Strict access, backups, monitoring |

## 7. Key Design Principles

1. **Thin routes, fat domain.** Routes validate, authenticate, call a service, map the response. No business logic in HTTP handlers.
2. **Tenant scope is mandatory.** Every repository method that accesses tenant data requires explicit `organization_id`.
3. **Idempotency everywhere.** Queue consumers, webhooks, feedback writes, and notifications all use idempotency keys or unique constraints.
4. **Immutable evidence.** Raw source observations are stored before parsing and never mutated. Corrections create new versions.
5. **Deterministic pipelines.** Identical evidence + same parser version = identical output. Version everything.
6. **Bounded failures.** A single source or parser failure cannot affect API availability or other source processing.
7. **Observable lineage.** Every opportunity can be traced from source job → raw snapshot → parsed listing → normalized listing → valuation → opportunity → notification → user action.
