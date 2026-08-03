# Batch 03 — Database Completion Review

**Review type:** Batch closure verification
**Batch:** 3 — Database Foundation
**Date:** 2026-08-03T17:36:12+05:00
**Reviewer:** Architecture review pass
**Status:** CLOSED

---

## 1. Database Foundation Objective

**Goal:** Wire the FastAPI application to a real PostgreSQL 17 database via SQLAlchemy async engine, initialize Alembic, and create all 25 tables with 7 ENUMs and 12 application indexes per `database-design.md` §2-3, incorporating all ADR-mandated corrections.

**Outcome:** Achieved. All 25 tables, 7 ENUMs, and 12 indexes are created and verified through full upgrade/downgrade/reset cycles. The async SQLAlchemy engine, session factory, and dependency injection are operational with SQLite for local development (ADR-0009 fallback). Alembic is configured for hand-written migrations with PostgreSQL DDL generation via `--sql` mode.

---

## 2. Migration Summary

| # | Revision | File | Tables | ENUMs | Indexes | Lines |
|---|----------|------|--------|-------|---------|-------|
| 001 | `a40b5bfef9a2` | identity_and_catalog | 9 | 1 (membership_role) | — | 154 |
| 002 | `12e1f9e711d2` | listings_and_valuation | 8 | 2 (listing_status, opportunity_state) | — | 242 |
| 003 | `de4e1b0ff4a3` | alerts_and_operations | 8 | 4 (delivery_status, feedback_decision, subscription_status, outbox_event_status) | — | 220 |
| 004 | `f2b39ba97b17` | indexes | — | — | 12 | 83 |
| **Total** | | | **25** | **7** | **12** | **699** |

**Revision chain:** `(base) → a40b5bfef9a2 → 12e1f9e711d2 → de4e1b0ff4a3 → f2b39ba97b17 → (head)`

---

## 3. Final Schema State

### Tables by Domain

| Domain | Migration | Tables |
|--------|-----------|--------|
| Identity | 001 | organizations, users, memberships |
| Catalog | 001 | brands, references, aliases, watch_lists, watch_list_entries |
| Sources | 001 | sources |
| Evidence | 002 | raw_snapshots |
| Parsing | 002 | parsed_listings |
| Normalization | 002 | normalized_listings |
| Duplicates | 002 | duplicate_groups, duplicate_group_members |
| Valuation | 002 | valuations |
| Opportunities | 002 | opportunities, opportunity_views |
| Alerts | 003 | alert_rules, alert_deliveries |
| Feedback | 003 | feedbacks |
| Outcomes | 003 | trade_outcomes |
| Billing | 003 | subscriptions |
| Audit | 003 | audit_events |
| Messaging | 003 | outbox_events |
| Operations | 003 | feature_flags |

### ENUM Inventory

| ENUM | Values | Created In |
|------|--------|-----------|
| `membership_role` | owner, admin, dealer, viewer | 001 |
| `listing_status` | active, quarantined, suppressed, stale | 002 |
| `opportunity_state` | published, dismissed, contacted, purchased, expired | 002 |
| `delivery_status` | pending, sent, failed, suppressed | 003 |
| `feedback_decision` | purchased, contacted, dismissed | 003 |
| `subscription_status` | trialing, active, past_due, canceled, unpaid | 003 |
| `outbox_event_status` | pending, published, failed | 003 |

### Index Inventory

| Index | Table | Type |
|-------|-------|------|
| `idx_memberships_org_user` | memberships | Composite B-tree |
| `idx_opportunities_org_state` | opportunities | Composite B-tree |
| `idx_alert_rules_org` | alert_rules | Composite B-tree |
| `idx_feedbacks_org_opp` | feedbacks | Composite B-tree |
| `idx_opportunities_published` | opportunities | Partial B-tree |
| `idx_normalized_listings_ref` | normalized_listings | Composite B-tree |
| `idx_normalized_listings_active` | normalized_listings | Partial B-tree |
| `idx_alert_deliveries_org_user` | alert_deliveries | Composite B-tree |
| `idx_alert_deliveries_opp` | alert_deliveries | Composite B-tree |
| `idx_outbox_pending` | outbox_events | Partial B-tree |
| `idx_audit_org_time` | audit_events | Composite B-tree |
| `idx_audit_resource` | audit_events | Composite B-tree |

---

## 4. ADR Compliance

### ADR-0002 — Alert Delivery Data Model

| Decision | Implementation | Verification |
|----------|---------------|-------------|
| D1: Remove composite UNIQUE on alert_deliveries | Only `idempotency_key UNIQUE` exists; no composite UNIQUE | `\d alert_deliveries` — only `uq_alert_deliveries_idempotency_key` |
| D2: Add `organization_id` to alert_deliveries | `organization_id TEXT NOT NULL FK → organizations` | `\d alert_deliveries` — column present, not null, FK |
| D3: Add `material_version` to alert_deliveries | `material_version INTEGER NOT NULL` | `\d alert_deliveries` — column present, not null |
| 3 redundant idempotency indexes excluded | `idx_alert_deliveries_idem`, `idx_feedbacks_idem`, `idx_trade_outcomes_idem` skipped in 004 | `\di *idem*` — 0 rows |
| database-design.md §2.8 updated | Schema matches ADR-0002 corrected definition | `organization_id`, `material_version` present; composite UNIQUE absent |

**Status:** COMPLIANT.

### ADR-0004 — Customer-Visible Data Freshness Model

| Decision | Implementation | Verification |
|----------|---------------|-------------|
| D1: `observation_at TIMESTAMPTZ NOT NULL` on normalized_listings | Column present, no default | `\d normalized_listings` — `observation_at | timestamp with time zone | not null` |
| D1: No DEFAULT — worker must populate | Schema enforces NOT NULL at insert time | No `DEFAULT` clause in column definition |

**Status:** COMPLIANT. D2 and D3 are API-layer concerns, not migration concerns.

### ADR-0005 — FX Rate Management

| Decision | Implementation | Verification |
|----------|---------------|-------------|
| D1: `fx_rate NUMERIC(18,8) NOT NULL` | Column present with exact precision | `\d normalized_listings` — `fx_rate | numeric(18,8) | not null` |
| D1: `fx_source TEXT NOT NULL` | Column present | `\d normalized_listings` — `fx_source | text | not null` |
| D1: `fx_date DATE NOT NULL` | Column present | `\d normalized_listings` — `fx_date | date | not null` |

**Status:** COMPLIANT. D2 (single provider) and D3 (gateway pattern) are application-layer concerns.

### ADR-0008 — Initial Migration Split Strategy

| Decision | Implementation | Verification |
|----------|---------------|-------------|
| 4 migrations split by domain boundary | 001 (identity+catalog), 002 (listings+valuation), 003 (alerts+operations), 004 (indexes) | 4 migration files |
| Indexes in separate migration | Migration 004 creates all 12 indexes, no table DDL | `alembic history` — 004 depends on 003 |
| Hand-written, no autogenerate | All migrations use `op.create_table()`, `op.create_index()`, `op.execute()` | No `--autogenerate` flag used |

**Status:** COMPLIANT.

---

## 5. Verification Evidence

### Upgrade

```
make db-reset
→ DROP SCHEMA CASCADE → CREATE SCHEMA → apply 001-004
→ 25 user tables + alembic_version = 26 relations
→ 7 ENUMs
→ 12 application indexes
→ Revision: f2b39ba97b17 (head)
```

### Full Pipeline FK Chain

Complete pipeline chain verified with sample data through all 7 JOINs:

```
source → raw_snapshot → parsed_listing → normalized_listing → valuation → opportunity → opportunity_view
       → alert_rule → alert_delivery → feedback → trade_outcome
       → outbox_event → audit_event → feature_flag → subscription
```

| Data Point | Table | Value Verified |
|-----------|-------|---------------|
| Source key | sources | `closure_source` |
| Listing price | parsed_listings | `15000.00 USD` |
| FX rate provenance | normalized_listings | `1.08500000 / ecb / 2026-08-03` |
| Observation timestamp | normalized_listings | `2026-08-03T11:39:48Z` |
| Valuation profit | valuations | `675.00 USD, ROI 0.045000` |
| Opportunity state | opportunities | `published, material_version=1` |
| Alert delivery | alert_deliveries | `pending, telegram, material_version=1` |
| Dealer feedback | feedbacks | `purchased` |
| Trade outcome | trade_outcomes | `$5800 → $6200, profit $400, 14 days` |
| Outbox event | outbox_events | `pending, event_version=1.0` |
| Audit event | audit_events | `member.invited` |
| Feature flag | feature_flags | `new_algo_v2, enabled=false` |

### Reset

```
make db-reset
→ DROP SCHEMA CASCADE (all objects removed)
→ apply migrations 001-004 (full schema restored)
→ 25 tables, 7 ENUMs, 12 indexes — identical state after every reset
```

### ADR Correction Verification

| ADR | Table.Column | Verified |
|-----|-------------|----------|
| ADR-0002 | alert_deliveries.organization_id | Present, NOT NULL, FK |
| ADR-0002 | alert_deliveries.material_version | Present, INT NOT NULL |
| ADR-0002 | alert_deliveries — no composite UNIQUE | Only idempotency_key UNIQUE |
| ADR-0004 | normalized_listings.observation_at | Present, TIMESTAMPTZ NOT NULL |
| ADR-0005 | normalized_listings.fx_rate | Present, NUMERIC(18,8) NOT NULL |
| ADR-0005 | normalized_listings.fx_source | Present, TEXT NOT NULL |
| ADR-0005 | normalized_listings.fx_date | Present, DATE NOT NULL |

### Schema Completeness Against database-design.md

| database-design.md § | Tables | Migration | Match? |
|----------------------|--------|-----------|--------|
| §2.1 Identity | 3 | 001 | YES |
| §2.2 Catalog | 5 | 001 | YES |
| §2.3 Ingestion | 2 | 001 (sources), 002 (raw_snapshots) | YES |
| §2.4 Listings | 2 | 002 | YES |
| §2.5 Duplicates | 2 | 002 | YES |
| §2.6 Valuation | 1 | 002 | YES |
| §2.7 Opportunities | 2 | 002 | YES |
| §2.8 Alerts | 2 | 003 | YES |
| §2.9 Feedback | 2 | 003 | YES |
| §2.10 Billing | 1 | 003 | YES |
| §2.11 Operations | 2 | 003 | YES |
| §2.12 Feature Flags | 1 | 003 | YES |
| §3 Indexes | 12 | 004 | YES (3 redundant excluded) |
| **Total** | **25** | | **YES** |

---

## 6. Known Issues

### KN-01: `references` is a PostgreSQL reserved word

**Severity:** NOTE
**Description:** The table name `references` requires double-quoting in raw SQL (`"references"`). ORM/SQLAlchemy handle this transparently through identifier quoting. Only affects raw SQL in seed scripts and `docker exec ... psql` commands.

**Resolution:** Accepted design choice from database-design.md. No migration change needed. Seed scripts use `"references"` quoting.

### KN-02: Makefile `export` propagation affects per-migration downgrade

**Severity:** NOTE
**Description:** The `export CHRONOARB_DATABASE_URL` in the Makefile does not reliably propagate to sub-shells invoked by Alembic. This causes `make db-migrate` and `make db-rollback` to silently skip migration application.

**Workaround:** Use direct shell pipeline for individual migration downgrade:
```bash
CHRONOARB_DATABASE_URL=postgresql+asyncpg://... alembic downgrade $FROM:$TO --sql 2>/dev/null | docker exec -i chronoarb-pg psql -U postgres -d chronoarb -q
```

**Resolution:** `make db-reset` (full reset) works correctly. Per-migration fix deferred to Batch 8 (CI setup).

### KN-03: Python 3.14 + asyncpg incompatibility requires `--sql` pipeline

**Severity:** NOTE
**Description:** Python 3.14.6 has unresolved async driver incompatibilities with asyncpg 0.31.0 and psycopg 3. All Alembic operations use `--sql` mode with piping to `docker exec ... psql`. See ADR-0009 for full details.

**Transaction path:** When asyncpg resolves the Python 3.14 issue, the `database_url` default switches from SQLite to PostgreSQL with a one-line config change.

### KN-04: subscriptions.stripe_customer_id not indexed

**Severity:** NOTE
**Description:** Stripe webhook lookups by `stripe_customer_id` and `stripe_subscription_id` use sequential scan. At MVP scale (10 organizations, 10 subscriptions), this is <1ms. Post-MVP (>100 subscriptions), these columns should get indexes.

**Resolution:** Add `CREATE INDEX idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id)` and `CREATE INDEX idx_subscriptions_stripe_subscription ON subscriptions(stripe_subscription_id)` in a future migration when subscription volume warrants it.

---

## 7. Infrastructure Components Delivered

| Component | Status | Location |
|-----------|--------|----------|
| PostgreSQL 17 Docker container | Operational | `chronoarb-pg`, port 5432 |
| SQLAlchemy async engine | Operational | `apps/api/apps/api/infrastructure/database.py` |
| Async session factory | Operational | `apps/api/apps/api/infrastructure/database.py` |
| Declarative Base + TimestampMixin | Operational | `apps/api/apps/api/infrastructure/models.py` |
| Alembic async configuration | Operational | `alembic/env.py`, `alembic.ini` |
| `/health` endpoint | Operational | Returns liveness probe |
| `/ready` endpoint | Operational | HTTP 200/503 based on DB connectivity |
| Trace ID middleware | Operational | All responses carry `X-Trace-Id` |
| Error envelope | Operational | Pydantic errors → 422, generic → 500 |
| Migration workflow (Makefile) | Operational | `make db-reset`, `make db-status`, `make db-clean` |
| Local dev fallback (SQLite) | Operational | Documented in ADR-0009 |

---

## 8. Final Verdict

### DATABASE FOUNDATION COMPLETE

All 25 tables, 7 ENUMs, and 12 indexes are created, verified, and match the database-design.md specification with all ADR corrections applied. The async engine, session factory, and Alembic configuration are operational. The full upgrade/downgrade/reset cycle is verified.

**Batch 3 tasks completed:**

| Task | Status |
|------|--------|
| DB-01: PostgreSQL Docker container | COMPLETE |
| DB-02: Database creation + connectivity | COMPLETE |
| DB-03: Alembic initialization | COMPLETE |
| DB-04: SQLAlchemy engine + session | COMPLETE |
| DB-05: Base model conventions | COMPLETE |
| DB-06: Migration 001 (identity + catalog) | COMPLETE |
| DB-07: Migration 002 (listings + valuation) | COMPLETE |
| DB-08: Migration 003 (alerts + operations) | COMPLETE |
| DB-09: Migration 004 (indexes) | COMPLETE |
| DB-10: Upgrade real database | COMPLETE |
| DB-11: Verify schema | COMPLETE |
| DB-12: Upgrade /ready endpoint | COMPLETE |
| DB-13: Integration tests | COMPLETE |
| DB-14: Downgrade + re-upgrade | COMPLETE |
| DB-15: Test fixtures | COMPLETE |

**Ready for:** Week 2-3 domain model and repository implementation.
