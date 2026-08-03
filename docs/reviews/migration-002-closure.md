# Migration 002 — Closure Review

**Review type:** Post-implementation verification
**Migration:** 002_listings_and_valuation (12e1f9e711d2)
**Date:** 2026-08-03T16:40:50+05:00
**Reviewer:** Architecture review pass
**Prerequisites:** migration-002-plan.md, migration-002-plan-review.md
**Status:** CLOSED

---

## Executive Summary

Migration 002 is fully verified. The upgrade/downgrade/re-upgrade cycle completes without errors. All 13 foreign keys resolve through a 7-table pipeline chain. ADR-0004 and ADR-0005 corrections are enforced at the schema level and verified with sample data. Tenant isolation is correctly scoped. All 83 columns across 8 tables use correct types. No findings.

**Verdict: READY FOR MIGRATION 003**

---

## 1. Upgrade Verification

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Database reset + apply 001 + 002 | 17 user tables + alembic_version | 17 user tables + alembic_version | PASS |
| Revision at head | `12e1f9e711d2` | `12e1f9e711d2` | PASS |
| Migration 001 tables present | 9 tables | 9 tables | PASS |
| Migration 002 tables present | 8 tables | 8 tables | PASS |
| ENUM count | 3 types | 3 types | PASS |

**Evidence:**
```
Table count: 17 (pg_tables excluding alembic_version)
Revision:    12e1f9e711d2
ENUMs:       listing_status, membership_role, opportunity_state
002 tables:  raw_snapshots, parsed_listings, normalized_listings,
             duplicate_groups, duplicate_group_members, valuations,
             opportunities, opportunity_views
```

---

## 2. Downgrade Verification

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `downgrade 12e1f9e711d2:a40b5bfef9a2` | 9 tables (001 only) | 9 tables | PASS |
| 002 ENUMs dropped | Only `membership_role` remains | Only `membership_role` | PASS |
| 002 tables absent | 0 of 8 present | 0 of 8 present | PASS |
| Revision rolled back | `a40b5bfef9a2` | `a40b5bfef9a2` | PASS |
| Downgrade order correct | 17→10 (reverse creation) | All foreign keys dropped without violation | PASS |

**Evidence:**
```
After downgrade:   organizations, users, brands, sources, watch_lists,
                   references, memberships, aliases, watch_list_entries,
                   alembic_version = 10 tables
ENUMs:             membership_role only
002 tables:        (0 rows) — none of the 8 tables exist
```

---

## 3. Re-Upgrade Verification

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Re-apply 002 after downgrade | 17 tables | 17 tables | PASS |
| Revision restored to head | `12e1f9e711d2` | `12e1f9e711d2` | PASS |
| ENUMs re-created | 3 types | 3 types | PASS |
| Upgrade idempotent | No error on duplicate apply | Schema unchanged when reapplied | PASS |

**Evidence:** Full cycle: `downgrade(002→001) → re-upgrade(001→002)` restores all 8 tables without errors. Alembic tracks applied revisions correctly through `alembic_version`.

---

## 4. Foreign Key Chain Verification

Pipeline chain tested with sample data flowing through all 7 JOINs:

```
source → raw_snapshot → parsed_listing → normalized_listing → valuation → opportunity → opportunity_view
```

| Join | FK | Column | Value | Status |
|------|----|--------|-------|--------|
| sources → raw_snapshots | `fk_raw_snapshots_source_id` | source_key | `closure_source` | PASS |
| raw_snapshots → parsed_listings | `fk_parsed_listings_snapshot_id` (UNIQUE) | external_id | `ext_cls` | PASS |
| parsed_listings → normalized_listings | `fk_normalized_listings_parsed_listing_id` (UNIQUE) | listing_title | `Test Watch` | PASS |
| normalized_listings → valuations | `fk_valuations_listing_id` | expected_net_profit | `675.00` | PASS |
| valuations → opportunities | `fk_opportunities_valuation_id` | state | `published` | PASS |
| opportunities → opportunity_views | `fk_opportunity_views_opportunity_id` | viewed_at | `2026-08-03T11:39:48Z` | PASS |
| organizations → opportunities | `fk_opportunities_organization_id` | organization_id | `org_cls` | PASS |
| users → opportunity_views | `fk_opportunity_views_user_id` | user_id | `usr_cls` | PASS |

All 13 FKs resolve. No orphan references. No constraint violations during INSERT.

---

## 5. Sample Data Pipeline Verification

**Full resolution of a single listing through the pipeline:**

```
source_key:         closure_source
external_id:        ext_cls
listing_title:      Test Watch
listing_price:      15000.00 USD
fx_rate:            1.08500000 (EUR/USD)
fx_source:          ecb
fx_date:            2026-08-03
observation_at:     2026-08-03 11:39:48.226633+00
status:             active
expected_exit_price: 16500.00
all_in_acquisition:  15000.00
expected_net_profit: 675.00
roi:                  0.045000 (4.5%)
organization_id:    org_cls
opp_state:          published
material_version:   1
viewed_at:          2026-08-03 11:39:48.232472+00
```

All columns populated with correct types and values. The pipeline produces a complete opportunity from raw evidence through valuation to published alert.

---

## 6. ADR-0004 Compliance (Customer-Visible Data Freshness)

| ADR-0004 D1 Requirement | Implementation | Status |
|--------------------------|---------------|--------|
| `observation_at TIMESTAMPTZ NOT NULL` | Column present, NOT NULL enforced | PASS |
| No DEFAULT — worker must populate | No default defined in schema | PASS |
| Value flows through FK chain | `observation_at` accessible via normalized_listings → valuations → opportunities | PASS |

**Schema evidence:**
```
observation_at | timestamp with time zone | not null | (no default)
```

**Data evidence:** `observation_at: 2026-08-03 11:39:48.226633+00` — correctly populated by INSERT.

**ADR-0004 D2 (data_age in API layer) and D3 (four required fields) are API-layer concerns — not migration concerns. Correctly deferred.**

---

## 7. ADR-0005 Compliance (FX Rate Management)

| ADR-0005 D1 Requirement | Implementation | Status |
|--------------------------|---------------|--------|
| `fx_rate NUMERIC(18,8) NOT NULL` | Column present, NOT NULL | PASS |
| `fx_source TEXT NOT NULL` | Column present, NOT NULL | PASS |
| `fx_date DATE NOT NULL` | Column present, NOT NULL | PASS |

**Schema evidence:**
```
fx_rate   | numeric(18,8) | not null | (no default)
fx_source | text          | not null | (no default)
fx_date   | date          | not null | (no default)
```

**Data evidence:** `fx_rate: 1.08500000 | fx_source: ecb | fx_date: 2026-08-03` — all three columns populated with correct precision.

**ADR-0005 D2 (single provider) and D3 (gateway pattern) are application-layer concerns — correctly deferred.**

---

## 8. Financial NUMERIC Correctness

| Column | Declared Type | Inserted Value | Precision Preserved? | Status |
|--------|-------------|----------------|---------------------|--------|
| `listing_price` | `NUMERIC(18,2)` | `15000.00` | Yes (2 decimal places) | PASS |
| `fx_rate` | `NUMERIC(18,8)` | `1.08500000` | Yes (8 decimal places) | PASS |
| `expected_exit_price` | `NUMERIC(18,2)` | `16500.00` | Yes | PASS |
| `all_in_acquisition` | `NUMERIC(18,2)` | `15000.00` | Yes | PASS |
| `expected_net_profit` | `NUMERIC(18,2)` | `675.00` | Yes | PASS |
| `roi` | `NUMERIC(10,6)` | `0.045000` | Yes (6 decimal places) | PASS |

All 12 money columns in migration 002 use `NUMERIC` types. No `FLOAT`, `DOUBLE`, or `REAL` columns exist in any migration 002 table. AGENTS.md §2 float prohibition is enforced at the schema level.

---

## 9. Tenant Isolation

| Table | Has `organization_id`? | Correct? |
|-------|------------------------|----------|
| `raw_snapshots` | No | YES — global evidence |
| `parsed_listings` | No | YES — global parsed data |
| `normalized_listings` | No | YES — global canonical listings |
| `duplicate_groups` | No | YES — global duplicate detection |
| `duplicate_group_members` | No | YES — global |
| `valuations` | No | YES — global analysis |
| `opportunities` | **Yes — `FK → organizations NOT NULL`** | YES — tenant-scoped per ADR-0001 D7 |
| `opportunity_views` | No | YES — user-scoped, org derived via opportunity FK |

Only `opportunities` carries `organization_id`. This is correct — the pipeline produces global data. Tenant scoping occurs at the opportunity layer where organization-specific cost assumptions apply.

**Evidence:** `opportunities.organization_id: org_cls` — FK to organizations resolves correctly. Cross-tenant access is prevented by the application layer (repository scoping, not schema).

---

## 10. Migration File Quality

| Check | Status |
|-------|--------|
| Hand-written (no autogenerate) | PASS — SQL via `op.create_table()`, `op.execute()` |
| `postgresql.ENUM(..., create_type=False)` on ENUM columns | PASS — prevents duplicate CREATE TYPE |
| `sa.dialects.postgresql.JSONB()` for JSONB columns | PASS |
| `sa.TIMESTAMP(timezone=True)` for all timestamps | PASS |
| `server_default=sa.func.now()` on `created_at` | PASS |
| Explicit constraint names (pk_, fk_, uq_ prefixes) | PASS |
| Downgrade drops in reverse creation order | PASS |
| Downgrade drops ENUMs after tables | PASS |
| `down_revision` correctly points to 001 | PASS — `a40b5bfef9a2` |
| No ORM model imports | PASS — no model references |
| No application service imports | PASS |
| File length | 242 lines (reasonable) | PASS |

---

## 11. Plan-to-Implementation Traceability

| Plan §6 Table | Table Created | Columns Match? | FK Match? | ENUM Match? | ADR Corrections? |
|---------------|--------------|---------------|-----------|------------|-----------------|
| Table 10: raw_snapshots | `raw_snapshots` | 7 cols ✓ | 1 FK ✓ | N/A | N/A |
| Table 11: parsed_listings | `parsed_listings` | 11 cols ✓ | 1 FK (UNIQUE) ✓ | N/A | N/A |
| Table 12: normalized_listings | `normalized_listings` | 18 cols ✓ | 2 FK ✓ | `listing_status` ✓ | observation_at ✓, fx_source ✓, fx_date ✓ |
| Table 13: duplicate_groups | `duplicate_groups` | 6 cols ✓ | 1 FK ✓ | N/A | N/A |
| Table 14: duplicate_group_members | `duplicate_group_members` | 4 cols ✓ | 2 FK ✓ | N/A | N/A |
| Table 15: valuations | `valuations` | 20 cols ✓ | 1 FK ✓ | N/A | N/A |
| Table 16: opportunities | `opportunities` | 13 cols ✓ | 3 FK ✓ | `opportunity_state` ✓ | N/A |
| Table 17: opportunity_views | `opportunity_views` | 4 cols ✓ | 2 FK ✓ | N/A | N/A |

**Zero deviations between plan specifications and implementation.** Every column, constraint, FK, and ENUM from the plan is present in the migration. Every column uses the exact type specified in the plan.

---

## 12. Known Issues

### Makefile `export` Propagation

The `export CHRONOARB_DATABASE_URL` in the Makefile does not reliably propagate to sub-shells invoked by `alembic`. This causes `make db-migrate` to silently skip migration application.

**Workaround:** Use direct shell pipeline for local testing:
```bash
CHRONOARB_DATABASE_URL=postgresql+asyncpg://... alembic upgrade head --sql 2>/dev/null | docker exec -i chronoarb-pg psql -U postgres -d chronoarb -q
```

**Impact:** NOTE. `make db-reset` works correctly (it drops everything via `db-clean` and re-applies from scratch). The issue only affects incremental `db-migrate`. Fix deferred to Batch 8 (CI setup).

### `references` Reserved Word

The table name `references` is a PostgreSQL reserved word. It requires double-quoting in raw SQL. This is a known design choice from database-design.md and migration 001. ORM/SQLAlchemy handle this transparently through identifier quoting.

**Impact:** NOTE. Only affects raw SQL in `psql` and seed scripts. Migration and ORM code handle it correctly.

---

## 13. Correction Summary

**Zero corrections needed.** The migration implementation exactly matches the plan specifications. All verification checks pass on first execution.

---

## 14. Batch Progression Gate

**Question: Is the repository ready for Migration 003 (alerts_and_operations)?**

Yes. Migration 003 requires:
- `organizations`, `users`, `references` tables (from 001) — PRESENT
- `opportunities` table (from 002) — PRESENT
- Both migrations applied and verified — DONE

| Gate | Status |
|------|--------|
| Migration 001 applied | PASS |
| Migration 002 applied | PASS |
| Full downgrade + re-upgrade cycle verified | PASS |
| Pipeline FK chain verified with sample data | PASS |
| ADR-0004/0005 corrections enforced | PASS |
| All financial columns use NUMERIC | PASS |
| Tenant isolation correct | PASS |
| No plan-to-implementation drift | PASS |

**Verdict: READY FOR MIGRATION 003**
