# ChronoArb — Migration 003 Implementation Plan

**Plan type:** Migration authoring guide
**Migration:** 003_alerts_and_operations
**Date:** 2026-08-03T16:45:24+05:00
**Status:** Ready for implementation
**References:** ADR-0002, ADR-0008, database-design.md §2.8-2.12

---

## 1. Migration Purpose

Migration 003 creates the **business process layer** — the tables that enable dealer workflows, notification delivery, billing, audit trails, event-driven processing, and feature rollout. These 8 tables complete the database schema (all 25 tables across 001/002/003). This migration depends on both 001 (identity + catalog) and 002 (listings + valuation) because:

- `alert_rules` references `organizations` and `users` (001)
- `alert_deliveries` references `organizations` (001), `alert_rules`, `users` (001), `opportunities` (002)
- `feedbacks` references `organizations` (001), `users` (001), `opportunities` (002)
- `trade_outcomes` references `organizations` (001), `users` (001), `opportunities` (002), `references` (001)
- `subscriptions` references `organizations` (001)
- `audit_events` references `organizations` and `users` (001, both nullable)
- `outbox_events` and `feature_flags` have no foreign keys

---

## 2. Tables Created

| # | Table | Domain | Record Count (MVP est.) |
|---|-------|--------|------------------------|
| 18 | `alert_rules` | Alerts | ~50 (5 rules × 10 orgs) |
| 19 | `alert_deliveries` | Notifications | ~500/day |
| 20 | `feedbacks` | Decisions | ~100/day |
| 21 | `trade_outcomes` | Outcomes | ~20/week |
| 22 | `subscriptions` | Billing | 1 per organization (~10) |
| 23 | `audit_events` | Audit | ~1K/day |
| 24 | `outbox_events` | Messaging | ~500 pending |
| 25 | `feature_flags` | Operations | ~20 total |

---

## 3. Dependency Order (Creation Sequence)

Tables must be created in this exact order to satisfy foreign key relationships:

```
18. alert_rules            ← FK → organizations (001, table 1), FK → users (001, table 2)
19. alert_deliveries       ← FK → organizations (001, table 1), FK → alert_rules (003, table 18),
                              FK → users (001, table 2), FK → opportunities (002, table 16)
20. feedbacks              ← FK → organizations (001, table 1), FK → users (001, table 2),
                              FK → opportunities (002, table 16)
21. trade_outcomes         ← FK → organizations (001, table 1), FK → users (001, table 2),
                              FK → opportunities (002, table 16, nullable),
                              FK → references (001, table 5)
22. subscriptions          ← FK → organizations (001, table 1)
23. audit_events           ← FK → organizations (001, table 1, nullable),
                              FK → users (001, table 2, nullable)
24. outbox_events          ← (no FKs)
25. feature_flags          ← (no FKs)
```

**Downgrade order:** 25 → 18 (reverse of creation).

---

## 4. ENUM Requirements

Four PostgreSQL native ENUMs must be created BEFORE the tables that reference them:

| ENUM | Values | Used By | Created Before |
|------|--------|---------|---------------|
| `delivery_status` | `pending`, `sent`, `failed`, `suppressed` | `alert_deliveries.delivery_status` | Table 19 |
| `feedback_decision` | `purchased`, `contacted`, `dismissed` | `feedbacks.decision` | Table 20 |
| `subscription_status` | `trialing`, `active`, `past_due`, `canceled`, `unpaid` | `subscriptions.status` | Table 22 |
| `outbox_event_status` | `pending`, `published`, `failed` | `outbox_events.status` | Table 24 |

**Creation pattern (upgrade):**
```python
op.execute("CREATE TYPE delivery_status AS ENUM ('pending', 'sent', 'failed', 'suppressed')")
op.execute("CREATE TYPE feedback_decision AS ENUM ('purchased', 'contacted', 'dismissed')")
op.execute("CREATE TYPE subscription_status AS ENUM ('trialing', 'active', 'past_due', 'canceled', 'unpaid')")
op.execute("CREATE TYPE outbox_event_status AS ENUM ('pending', 'published', 'failed')")
```

**Drop pattern (downgrade):**
```python
op.execute("DROP TYPE outbox_event_status")
op.execute("DROP TYPE subscription_status")
op.execute("DROP TYPE feedback_decision")
op.execute("DROP TYPE delivery_status")
```

Use `create_type=False` on ENUM column definitions to prevent Alembic from auto-creating types already created manually.

---

## 5. Foreign Keys

| Table | FK Count | FK Target Tables |
|-------|----------|-----------------|
| `alert_rules` | 2 | `organizations(id)`, `users(id)` — created_by |
| `alert_deliveries` | 4 | `organizations(id)`, `alert_rules(id)`, `users(id)`, `opportunities(id)` |
| `feedbacks` | 3 | `organizations(id)`, `users(id)`, `opportunities(id)` |
| `trade_outcomes` | 4 | `organizations(id)`, `users(id)`, `opportunities(id)` — nullable, `references(id)` |
| `subscriptions` | 1 | `organizations(id)` |
| `audit_events` | 2 | `organizations(id)` — nullable, `users(id)` — nullable |
| `outbox_events` | 0 | — |
| `feature_flags` | 0 | — |

**FK naming convention:** `fk_{table}_{column_name}`.

---

## 6. Constraints

### Table 18: alert_rules

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_alert_rules` |
| `organization_id` | `TEXT` | NOT NULL, FK → `organizations(id)` |
| `created_by` | `TEXT` | NOT NULL, FK → `users(id)` |
| `name` | `TEXT` | NOT NULL |
| `filters` | `JSONB` | NOT NULL (reference_ids, min_profit, max_acquisition, conditions) |
| `channels` | `JSONB` | NOT NULL ([{type: telegram, id: ...}, {type: push}]) |
| `cooldown_minutes` | `INT` | NOT NULL, DEFAULT 60 |
| `is_enabled` | `BOOLEAN` | DEFAULT true |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |

**Business purpose:** Dealer-defined rules that match opportunities to notification preferences. A rule says "alert me when a Rolex Submariner 116610LN is listed below $12,000 in pre_owned condition, via Telegram, no more than once per hour."

---

### Table 19: alert_deliveries

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_alert_deliveries` |
| `organization_id` | `TEXT` | NOT NULL, FK → `organizations(id)` **(ADR-0002 D2)** |
| `rule_id` | `TEXT` | NOT NULL, FK → `alert_rules(id)` |
| `user_id` | `TEXT` | NOT NULL, FK → `users(id)` |
| `opportunity_id` | `TEXT` | NOT NULL, FK → `opportunities(id)` |
| `material_version` | `INT` | NOT NULL **(ADR-0002 D3)** |
| `channel` | `TEXT` | NOT NULL (telegram, push) |
| `idempotency_key` | `TEXT` | UNIQUE NOT NULL |
| `delivery_status` | `delivery_status` | NOT NULL |
| `provider_message_id` | `TEXT` | Nullable |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |

**ADR-0002 corrections highlighted:**
- `organization_id` — added per ADR-0002 D2 (direct tenant scoping, no JOIN needed)
- `material_version` — added per ADR-0002 D3 (queryable without joining to opportunities)
- **No composite UNIQUE** — removed per ADR-0002 D1 (idempotency_key is sole uniqueness constraint)

**Business purpose:** Records that a specific alert rule matched a specific opportunity and a notification was (or will be) sent to a specific user through a specific channel. The idempotency key prevents duplicate deliveries for the same rule+user+opportunity+version+channel combination. `provider_message_id` stores the external delivery ID (Telegram message ID, FCM token) for delivery confirmation.

---

### Table 20: feedbacks

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_feedbacks` |
| `organization_id` | `TEXT` | NOT NULL, FK → `organizations(id)` |
| `user_id` | `TEXT` | NOT NULL, FK → `users(id)` |
| `opportunity_id` | `TEXT` | NOT NULL, FK → `opportunities(id)` |
| `decision` | `feedback_decision` | NOT NULL |
| `notes` | `TEXT` | Nullable |
| `idempotency_key` | `TEXT` | UNIQUE NOT NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |

**Business purpose:** Dealer decisions on opportunities — purchased, contacted (the seller), or dismissed. Each decision is recorded once (idempotency key). Notes allow the dealer to add context (e.g., "Seller wants wire transfer only, passing"). Feedback data feeds the learning pipeline — contact-to-purchase conversion rates, dismissal patterns, reference-specific win rates.

---

### Table 21: trade_outcomes

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_trade_outcomes` |
| `organization_id` | `TEXT` | NOT NULL, FK → `organizations(id)` |
| `user_id` | `TEXT` | NOT NULL, FK → `users(id)` |
| `opportunity_id` | `TEXT` | NULLABLE, FK → `opportunities(id)` |
| `reference_id` | `TEXT` | NOT NULL, FK → `references(id)` |
| `acquisition_price` | `NUMERIC(18,2)` | Nullable |
| `acquisition_currency` | `CHAR(3)` | Nullable |
| `resale_price` | `NUMERIC(18,2)` | Nullable |
| `resale_currency` | `CHAR(3)` | Nullable |
| `actual_profit` | `NUMERIC(18,2)` | Nullable |
| `days_to_sell` | `INT` | Nullable |
| `idempotency_key` | `TEXT` | UNIQUE NOT NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |

**Business purpose:** Realized trade outcomes — what the dealer actually paid, what they actually sold for, and how long it took. `opportunity_id` is nullable because a dealer may record an outcome for a trade they did independently (not from a ChronoArb opportunity). This data feeds the valuation model calibration — the gap between predicted profit and actual profit drives model improvements.

---

### Table 22: subscriptions

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_subscriptions` |
| `organization_id` | `TEXT` | NOT NULL, FK → `organizations(id)` |
| `stripe_customer_id` | `TEXT` | Nullable |
| `stripe_subscription_id` | `TEXT` | Nullable |
| `status` | `subscription_status` | NOT NULL |
| `plan_id` | `TEXT` | Nullable |
| `current_period_start` | `TIMESTAMPTZ` | Nullable |
| `current_period_end` | `TIMESTAMPTZ` | Nullable |
| `trial_end` | `TIMESTAMPTZ` | Nullable |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |

**Business purpose:** Stripe billing state for each organization. One subscription per organization (MVP — no multi-plan). The `status` field drives entitlement gates (feature access based on subscription state). Stripe IDs are nullable because subscriptions may exist before Stripe integration is wired (e.g., during development with mock billing).

---

### Table 23: audit_events

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_audit_events` |
| `organization_id` | `TEXT` | NULLABLE, FK → `organizations(id)` |
| `user_id` | `TEXT` | NULLABLE, FK → `users(id)` |
| `action` | `TEXT` | NOT NULL |
| `resource_type` | `TEXT` | NOT NULL |
| `resource_id` | `TEXT` | NOT NULL |
| `details` | `JSONB` | Nullable |
| `trace_id` | `TEXT` | Nullable |
| `client_ip` | `TEXT` | Nullable |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |

**Business purpose:** Immutable audit trail for privileged actions. Both organization_id and user_id are nullable because some audit events may originate from system processes (no user, no org). Examples: member.invited, member.role_changed, source.enabled, job.replayed, billing.state_changed.

**Nullability rationale by event type:**
| Event | organization_id | user_id |
|-------|----------------|---------|
| member.invited | Present (target org) | Present (inviter) |
| source.enabled | NULL (platform ops) | Present (ops engineer) |
| job.replayed | NULL (automated) | NULL (system process) |

---

### Table 24: outbox_events

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_outbox_events` |
| `event_name` | `TEXT` | NOT NULL |
| `event_version` | `TEXT` | NOT NULL |
| `payload` | `JSONB` | NOT NULL |
| `trace_id` | `TEXT` | Nullable |
| `status` | `outbox_event_status` | NOT NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |
| `published_at` | `TIMESTAMPTZ` | Nullable |

**Business purpose:** Transactional outbox pattern — guarantees at-least-once event publishing. Application services write events to this table in the same database transaction as the state change. The outbox worker polls for `pending` events and publishes them to SQS. `published_at` records when the event was successfully published. `status` transitions: pending → published (success) or pending → failed (after retry exhaustion).

---

### Table 25: feature_flags

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_feature_flags` |
| `key` | `TEXT` | UNIQUE NOT NULL |
| `description` | `TEXT` | Nullable |
| `enabled` | `BOOLEAN` | DEFAULT false |
| `organization_ids` | `JSONB` | Nullable (null = all orgs, array = specific orgs) |
| `rollout_pct` | `INT` | DEFAULT 0 |
| `expires_at` | `TIMESTAMPTZ` | Nullable |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |

**Business purpose:** Feature flag management for progressive rollouts and kill switches. Supports global flags (`organization_ids = NULL`), org-specific flags (JSONB array), and percentage rollouts (`rollout_pct`). `expires_at` enables self-expiring flags for temporary experiments.

---

## 7. Indexes

Indexes are created in migration 004, not inline. However, the following indexes will apply to migration 003 tables:

| Index | Table | Columns |
|-------|-------|---------|
| `idx_alert_rules_org` | alert_rules | (organization_id, is_enabled) |
| `idx_alert_deliveries_idem` | alert_deliveries | (idempotency_key) |
| `idx_alert_deliveries_org_user` | alert_deliveries | (organization_id, user_id, created_at DESC) |
| `idx_alert_deliveries_opp` | alert_deliveries | (opportunity_id, material_version) |
| `idx_feedbacks_org_opp` | feedbacks | (organization_id, opportunity_id) |
| `idx_feedbacks_idem` | feedbacks | (idempotency_key) |
| `idx_trade_outcomes_idem` | trade_outcomes | (idempotency_key) |
| `idx_outbox_pending` | outbox_events | (status, created_at) WHERE status = 'pending' |
| `idx_audit_org_time` | audit_events | (organization_id, created_at DESC) |
| `idx_audit_resource` | audit_events | (resource_type, resource_id) |

**No indexes are created in migration 003.** Migration 004 adds all indexes after all 25 tables exist.

---

## 8. Upgrade Verification

After applying migration 003 (on top of 001 + 002):

```bash
# Table count — 25 total (9 from 001 + 8 from 002 + 8 from 003)
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\dt" | wc -l
# Expected: 26 (25 tables + header)

# ENUM verification — 7 total
docker exec chronoarb-pg psql -U postgres -d chronoarb -c \
  "SELECT typname FROM pg_type WHERE typtype='e' ORDER BY typname;"
# Expected:
#   delivery_status
#   feedback_decision
#   listing_status
#   membership_role
#   opportunity_state
#   outbox_event_status
#   subscription_status

# ADR-0002 correction verification — alert_deliveries
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d alert_deliveries"
# Must show:
#   organization_id    | text                     | not null   ← ADR-0002 D2
#   material_version   | integer                  | not null   ← ADR-0002 D3
#   idempotency_key    | text                     | not null   ← sole UNIQUE
#   NO composite UNIQUE on (rule_id, user_id, ...) ← ADR-0002 D1

# Table structure verification
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d alert_rules"
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d feedbacks"
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d subscriptions"
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d audit_events"
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d outbox_events"
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d feature_flags"

# FK verification — alert_deliveries (most complex table)
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d alert_deliveries"
# Must show 4 foreign keys: organization_id, rule_id, user_id, opportunity_id

# FK verification — trade_outcomes
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d trade_outcomes"
# Must show 4 foreign keys: organization_id, user_id, opportunity_id (nullable), reference_id
```

---

## 9. Downgrade Verification

After downgrading migration 003:

```bash
# Table count — back to 17 (001 + 002 only)
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\dt" | wc -l
# Expected: 18 (17 tables + header)

# ENUM verification — only 3 remain
docker exec chronoarb-pg psql -U postgres -d chronoarb -c \
  "SELECT typname FROM pg_type WHERE typtype='e' ORDER BY typname;"
# Expected:
#   listing_status
#   membership_role
#   opportunity_state

# Verify no tables from 003 remain
docker exec chronoarb-pg psql -U postgres -d chronoarb -c \
  "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN
   ('alert_rules','alert_deliveries','feedbacks','trade_outcomes',
    'subscriptions','audit_events','outbox_events','feature_flags');"
# Expected: (0 rows)
```

---

## 10. Operational Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **ADR-0002: alert_deliveries UNIQUE constraint** | **CRITICAL** | The database-design.md §2.8 still shows the old composite UNIQUE on `(rule_id, user_id, opportunity_id, channel, material_version)`. ADR-0002 removed this. The migration MUST NOT include this constraint. Verify with `\d alert_deliveries` after upgrade — only `idempotency_key` should have a UNIQUE constraint. |
| **audit_events growth rate** | MINOR | At ~1K/day with JSONB details, the audit table will grow ~10MB/month. No partitioning at MVP (per database-design.md §6). Add a retention policy note: audit_events older than 90 days may be archived to S3 in v1.1. |
| **outbox_events contention** | MINOR | The outbox worker polls `WHERE status = 'pending' ORDER BY created_at`. With ~500 pending events and a single worker, contention is minimal at MVP scale. If pending events exceed 10K, add a `LIMIT 100` to the worker query (application concern, not schema concern). |
| **feature_flags without audit** | NOTE | Feature flag changes (`enabled`, `rollout_pct`) are not automatically audited. Operators must manually log changes. Consider adding an `audit_events` INSERT trigger on `feature_flags` in v1.1. |
| **subscriptions.updated_at on Stripe webhook** | NOTE | The `updated_at` column uses `server_default=NOW()` on insert and should use `onupdate=NOW()` via application code. Alembic's `server_default` applies on INSERT only. The Stripe webhook handler must explicitly set `updated_at = NOW()` on updates. |
| **idempotency_key length** | NOTE | TEXT column with no length limit. The application generates keys as `SHA256(org + user + rule + opp + material_version + channel)` which produces a 64-character hex string. TEXT is appropriate — no VARCHAR truncation risk. |

---

## 11. Re-Upgrade Idempotency

If migration 003 is reapplied (after downgrade), it must produce identical results:

```bash
# After applying 001 + 002:
make db-reset                               # Full reset, applies 001 + 002
make db-migrate                             # Applies 003
# Verify 25 tables

# Downgrade just 003:
docker exec chronoarb-pg psql -U postgres -d chronoarb -t -c "SELECT version_num FROM alembic_version;"
# → 12e1f9e711d2 (or current 003 revision)
# Manual downgrade via --sql

# Re-apply 003:
make db-migrate                             # Applies 003
# Verify 25 tables (identical state)
```

---

## 12. ADR Compliance Checklist

| ADR | Requirement | Table | Column | Verification |
|-----|-------------|-------|--------|-------------|
| ADR-0001 D2 | PostgreSQL only | All | — | `\dt` count |
| ADR-0001 D3 | NUMERIC for money | trade_outcomes | acquisition_price, resale_price, actual_profit | `\d trade_outcomes` |
| ADR-0001 D4 | TEXT PKs (ULID) | All | id | `\d alert_rules` |
| ADR-0001 D7 | organization_id on tenant tables | alert_rules, alert_deliveries, feedbacks, trade_outcomes, subscriptions | organization_id | `\d feedbacks` |
| ADR-0002 D1 | No composite UNIQUE on alert_deliveries | alert_deliveries | — | `\d alert_deliveries` |
| ADR-0002 D2 | organization_id on alert_deliveries | alert_deliveries | organization_id | `\d alert_deliveries` |
| ADR-0002 D3 | material_version on alert_deliveries | alert_deliveries | material_version | `\d alert_deliveries` |
| ADR-0008 | 4 migrations split by domain | 003 | — | `alembic history` |

---

## 13. Table Summary

| Table | Columns | PK | FKs | UNIQUEs | ENUMs | Money | Tenant |
|-------|---------|----|-----|---------|-------|-------|--------|
| `alert_rules` | 9 | 1 | 2 | 0 | 0 | 0 | YES (org_id) |
| `alert_deliveries` | 11 | 1 | 4 | 1 | 1 | 0 | YES (org_id) |
| `feedbacks` | 8 | 1 | 3 | 1 | 1 | 0 | YES (org_id) |
| `trade_outcomes` | 13 | 1 | 4 | 1 | 0 | 3 | YES (org_id) |
| `subscriptions` | 11 | 1 | 1 | 0 | 1 | 0 | YES (org_id) |
| `audit_events` | 10 | 1 | 2 | 0 | 0 | 0 | PARTIAL (nullable) |
| `outbox_events` | 8 | 1 | 0 | 0 | 1 | 0 | NO |
| `feature_flags` | 8 | 1 | 0 | 1 | 0 | 0 | NO |
| **Totals** | **78** | **8** | **16** | **4** | **4** | **3** | **5+1** |

**Grand total across all 3 migrations:** 25 tables, 298 columns, 7 ENUMs, 39 foreign keys.
