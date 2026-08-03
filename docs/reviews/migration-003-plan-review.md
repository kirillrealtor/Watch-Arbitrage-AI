# Migration 003 — Plan Review

**Review type:** Pre-implementation schema audit
**Reviewed document:** docs/implementation/migration-003-plan.md
**Date:** 2026-08-03T17:03:35+05:00
**Reviewer:** Architecture review pass
**Cross-referenced:** database-design.md §2.8-2.12, ADR-0002, ADR-0008

---

## Executive Summary

The migration 003 plan is correct and complete. Table dependency ordering resolves all 16 foreign keys without violations. ADR-0002 corrections are accurately encoded despite the database-design.md still showing the pre-correction schema. Four ENUMs have correct lifecycle. All business-purpose descriptions are consistent with the SRS. One minor issue: `alert_rules` has a redundant `organization_id` denormalization path (org_id exists both on alert_rules and alert_deliveries) which is deliberate but should be noted. No blocking issues.

**Verdict: READY FOR IMPLEMENTATION**

---

## 1. Table Dependency Ordering

### Cross-Reference Against Available Tables

| Table | FK Target | Exists After | Satisfied? |
|-------|----------|-------------|------------|
| 18: alert_rules → organizations | 001, table 1 | 001 applied | YES |
| 18: alert_rules → users | 001, table 2 | 001 applied | YES |
| 19: alert_deliveries → organizations | 001, table 1 | 001 applied | YES |
| 19: alert_deliveries → alert_rules | 003, table 18 | Within 003, created first | YES |
| 19: alert_deliveries → users | 001, table 2 | 001 applied | YES |
| 19: alert_deliveries → opportunities | 002, table 16 | 002 applied | YES |
| 20: feedbacks → organizations | 001, table 1 | 001 applied | YES |
| 20: feedbacks → users | 001, table 2 | 001 applied | YES |
| 20: feedbacks → opportunities | 002, table 16 | 002 applied | YES |
| 21: trade_outcomes → organizations | 001, table 1 | 001 applied | YES |
| 21: trade_outcomes → users | 001, table 2 | 001 applied | YES |
| 21: trade_outcomes → opportunities (nullable) | 002, table 16 | 002 applied | YES |
| 21: trade_outcomes → references | 001, table 5 | 001 applied | YES |
| 22: subscriptions → organizations | 001, table 1 | 001 applied | YES |
| 23: audit_events → organizations (nullable) | 001, table 1 | 001 applied | YES |
| 23: audit_events → users (nullable) | 001, table 2 | 001 applied | YES |
| 24: outbox_events | No FKs | — | YES |
| 25: feature_flags | No FKs | — | YES |

**Finding:** All 16 foreign keys reference tables that exist when the parent table is created. Zero cross-003 circular dependencies. The only intra-003 FK (alert_deliveries → alert_rules) is satisfied by creating alert_rules first.

**PASS.**

---

## 2. Alert Delivery Idempotency

### database-design.md vs ADR-0002 vs Plan

| Concern | database-design.md §2.8 | ADR-0002 | Migration Plan | Correct? |
|---------|------------------------|----------|---------------|----------|
| organization_id column | **Missing** | Required (D2) | Present, NOT NULL, FK | YES |
| material_version column | **Missing** | Required (D3) | Present, INT NOT NULL | YES |
| Composite UNIQUE | `(rule_id, user_id, opportunity_id, channel, material_version)` | **REMOVED** (D1) | Only `idempotency_key UNIQUE` | YES |
| Sole uniqueness | `idempotency_key UNIQUE` + composite | `idempotency_key UNIQUE` only | `idempotency_key UNIQUE` only | YES |

**Finding:** The migration plan correctly follows ADR-0002, not the outdated database-design.md. All three D1/D2/D3 corrections are encoded. The database-design.md §2.8 should be updated post-migration to reflect ADR-0002 (noted as a follow-up, not a plan defect).

**PASS.**

---

## 3. Tenant Isolation

| Table | Has `organization_id`? | Nullable? | Assessment |
|-------|------------------------|-----------|------------|
| `alert_rules` | Yes | NOT NULL | Correct — rules are per-org |
| `alert_deliveries` | Yes | NOT NULL | Correct — ADR-0002 D2 mandates this |
| `feedbacks` | Yes | NOT NULL | Correct — feedback is per-org action |
| `trade_outcomes` | Yes | NOT NULL | Correct — outcomes are per-org financial data |
| `subscriptions` | Yes | NOT NULL | Correct — 1 subscription per org |
| `audit_events` | Yes | NULLABLE | Correct — system events have no org |
| `outbox_events` | No | — | Correct — events are infrastructure, not tenant data |
| `feature_flags` | No | — | Correct — flags govern platform behavior, not tenant data |

**Issue CR-01: Redundant organization_id on alert_deliveries.** (NOTE)

`alert_deliveries.organization_id` is denormalized from `alert_rules.organization_id`. This is deliberate per ADR-0002 D2 rationale: "Eliminates the need to JOIN through alert_rules for tenant-scoped queries." However, it means the same organization could be referenced from two different paths:

```
alert_deliveries.organization_id → organizations (direct)
alert_deliveries.rule_id → alert_rules.organization_id → organizations (indirect)
```

The application must ensure these never diverge. The alert matcher worker populates both at insert time from the same source. No schema constraint can enforce consistency between the two paths. This is accepted risk per ADR-0002.

**PASS (with noted denormalization risk).**

---

## 4. Material Version Handling

| Requirement | Implementation | Status |
|-------------|---------------|--------|
| `material_version INT NOT NULL` on `alert_deliveries` | Present | PASS |
| Populated from `opportunities.material_version` at match time | Documented in business purpose | PASS |
| Enables version-specific delivery queries | No JOIN to opportunities needed | PASS |
| Not used for uniqueness | `idempotency_key` is sole UNIQUE | PASS |

**Finding:** ADR-0002 D3 is correctly implemented. `material_version` is a query-performance column, not a uniqueness column. The idempotency_key encodes the version in its hash, providing the actual uniqueness guarantee.

**PASS.**

---

## 5. ENUM Lifecycle

| ENUM | Values | Created Before | Dropped After | Correct? |
|------|--------|---------------|---------------|----------|
| `delivery_status` | pending, sent, failed, suppressed | Table 19 (alert_deliveries) | Table 19 | YES |
| `feedback_decision` | purchased, contacted, dismissed | Table 20 (feedbacks) | Table 20 | YES |
| `subscription_status` | trialing, active, past_due, canceled, unpaid | Table 22 (subscriptions) | Table 22 | YES |
| `outbox_event_status` | pending, published, failed | Table 24 (outbox_events) | Table 24 | YES |

**Drop order verification:** The plan specifies dropping outbox_event_status first, then subscription_status, then feedback_decision, then delivery_status. This is the reverse of creation order. No table uses a type after it's dropped — all consuming tables are dropped before their types.

**Downgrade order:** Tables 25→18 reversed, then ENUMs dropped. Correct.

**PASS.**

---

## 6. Subscription Design

### Schema Alignment with Stripe Billing

| Column | Aligns with Stripe? | Assessment |
|--------|-------------------|------------|
| `stripe_customer_id` | Yes — `cus_xxx` | Standard Stripe integration |
| `stripe_subscription_id` | Yes — `sub_xxx` | Standard Stripe integration |
| `status` ENUM | Covers all Stripe states | trialing, active, past_due, canceled, unpaid — complete |
| `plan_id` | Yes — Stripe Price ID | `price_xxx` |
| `current_period_start/end` | Yes — Stripe timestamp fields | Standard |
| `trial_end` | Yes — Stripe timestamp field | Standard |

**Note:** The plan states subscriptions.stripe_ids are nullable "because subscriptions may exist before Stripe integration is wired." This is acceptable for MVP development but should have a CHECK constraint added post-Stripe-integration to ensure production records always have Stripe IDs.

**PASS.**

---

## 7. Outbox Event Correctness

### Transactional Outbox Pattern Verification

| Requirement | Implementation | Status |
|-------------|---------------|--------|
| Events written in same transaction as state change | Application concern — schema supports it | PASS |
| `status` tracks lifecycle | pending → published (success), pending → failed (exhausted) | PASS |
| `published_at` records completion | TIMESTAMPTZ NULLABLE — NULL until published | PASS |
| `payload` is required | JSONB NOT NULL | PASS |
| `event_version` for schema evolution | TEXT NOT NULL | PASS |
| Worker polls `WHERE status = 'pending'` | Application concern — index supports it | PASS |
| `trace_id` for correlation | TEXT nullable | PASS |

**Finding:** Schema correctly supports the transactional outbox pattern. No FKs on outbox_events (events shouldn't reference application tables directly — they carry identifiers in the payload). The `event_version` field enables schema evolution of event payloads without requiring migration changes.

**PASS.**

---

## 8. Audit Event Design

### Immutable Audit Trail

| Requirement | Implementation | Status |
|-------------|---------------|--------|
| Immutable — no UPDATE path | Application concern — schema supports with INSERT-only pattern | PASS |
| Nullable FKs for system events | organization_id and user_id are both nullable | PASS |
| Structured action + resource tracking | `action`, `resource_type`, `resource_id` — all TEXT NOT NULL | PASS |
| Trace correlation | `trace_id` TEXT nullable | PASS |
| Client tracking | `client_ip` TEXT nullable | PASS |
| Rich details | `details` JSONB nullable | PASS |

**Example audit events the schema supports:**
```
action="member.invited", resource_type="membership", resource_id="mem_01J...", org_id="org_01J...", user_id="usr_01J..."
action="source.enabled", resource_type="source", resource_id="src_01J...", org_id=NULL, user_id="usr_ops"
action="job.replayed", resource_type="job", resource_id="job_01J...", org_id=NULL, user_id=NULL
```

**Finding:** Schema supports the full audit event taxonomy from security-model.md §16. Nullable FKs correctly handle system-initiated events.

**PASS.**

---

## 9. Feedback/Trade Outcome Relationships

### Relationship Validation

| Relationship | Implementation | Status |
|-------------|---------------|--------|
| feedbacks → opportunities | FK NOT NULL — every decision is on an opportunity | PASS |
| trade_outcomes → opportunities | FK NULLABLE — trade may be from non-ChronoArb source | PASS |
| trade_outcomes → references | FK NOT NULL — every trade has a watch reference | PASS |
| Both have idempotency keys | UNIQUE NOT NULL on both tables | PASS |

**Business rule enforcement:**
- `feedbacks.opportunity_id` is NOT NULL: Every dealer decision is tied to a specific opportunity. You can't record "purchased" without saying what you purchased.
- `trade_outcomes.opportunity_id` is NULLABLE: A dealer may record an outcome for a trade they made independently (e.g., a watch they found at a physical auction). This supports the learning pipeline without forcing ChronoArb to be the only source of deals.

**Finding:** The nullable vs not-null distinction between feedbacks and trade_outcomes is semantically correct and matches the SRS description of these entities.

**PASS.**

---

## 10. Downgrade Safety

### Table Drop Order

| Drop Order | Table | FKs Pointing To It | Satisfied? |
|------------|-------|--------------------|------------|
| 1st | `feature_flags` | None | YES |
| 2nd | `outbox_events` | None | YES |
| 3rd | `audit_events` | None (nullable FKs don't block) | YES |
| 4th | `subscriptions` | None | YES |
| 5th | `trade_outcomes` | None | YES |
| 6th | `feedbacks` | None | YES |
| 7th | `alert_deliveries` | None | YES |
| 8th | `alert_rules` | Referenced by alert_deliveries (already dropped) | YES |

### ENUM Drop Order

| Drop Order | ENUM | Consumed By | Table Dropped? |
|------------|------|------------|----------------|
| 9th | `outbox_event_status` | outbox_events | YES (2nd) |
| 10th | `subscription_status` | subscriptions | YES (4th) |
| 11th | `feedback_decision` | feedbacks | YES (6th) |
| 12th | `delivery_status` | alert_deliveries | YES (7th) |

**Finding:** Full downgrade is safe. All child tables are dropped before their parents. All ENUMs are dropped after their consuming tables. No cascade needed. No deferred constraint violations.

**PASS.**

---

## 11. Additional Findings

### Issue CR-02: Table count cross-reference with database-design.md. (NOTE)

The database-design.md §2.8 alert_deliveries schema (lines 234-244) is out of date — it does not include `organization_id` or `material_version` and still shows the composite UNIQUE. ADR-0002 (dated 2026-08-03) resolved these. The migration plan correctly follows ADR-0002.

**Action:** Update database-design.md §2.8 alert_deliveries definition to match ADR-0002 corrected schema. Not a plan defect — the plan is correct.

### Issue CR-03: alert_rules.updated_at has DEFAULT NOW() but no ON UPDATE. (NOTE)

The plan specifies `updated_at TIMESTAMPTZ NOT NULL, DEFAULT NOW()`. The `server_default=sa.func.now()` applies on INSERT only. When an alert rule is updated (name change, filter change, enabled toggle), the application must explicitly set `updated_at = NOW()`. This is the correct Alembic pattern — `onupdate` is handled at the application layer, not in DDL.

Same pattern applies to `subscriptions.updated_at`.

---

## 12. Correction Summary

| ID | Severity | Description | Action |
|----|----------|-------------|--------|
| CR-01 | NOTE | Denormalized organization_id on alert_deliveries (redundant with alert_rules path) | Acknowledged — ADR-0002 D2 rationale accepted |
| CR-02 | NOTE | database-design.md §2.8 still shows pre-ADR-0002 schema | Update database-design.md post-migration |
| CR-03 | NOTE | updated_at columns use DEFAULT NOW() only — no ON UPDATE | Application must set updated_at on UPDATE (standard Alembic pattern) |

**Zero blocking or major issues.** All three findings are notes for documentation or application-layer behavior.

---

## 13. Batch Progression Gate

**Question: Is migration 003 ready for implementation?**

Yes. All 10 review dimensions pass.

| Gate | Status |
|------|--------|
| Table dependency ordering correct | PASS (16 FKs, all resolve) |
| Alert delivery idempotency (ADR-0002) | PASS (D1/D2/D3 encoded) |
| Tenant isolation enforced | PASS (5 mandatory + 1 nullable) |
| Material version handling correct | PASS |
| ENUM lifecycle manageable | PASS (4 ENUMs, correct creation/drop) |
| Subscription design aligned with Stripe | PASS |
| Outbox event correctness | PASS |
| Audit event design supports all event types | PASS |
| Feedback/trade outcome relationships correct | PASS |
| Downgrade safe | PASS (25→18 reverse, ENUMs last) |

**Verdict: READY FOR IMPLEMENTATION**

The database-design.md §2.8 is the only documentation out of date — the plan correctly follows ADR-0002. Implementation should proceed directly from the plan's §6 (Table Specifications).
