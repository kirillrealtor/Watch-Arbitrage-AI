# ChronoArb — Migration 002 Implementation Plan

**Plan type:** Migration authoring guide
**Migration:** 002_listings_and_valuation
**Date:** 2026-08-03T16:26:26+05:00
**Status:** Ready for implementation
**References:** ADR-0004, ADR-0005, ADR-0008, database-design.md §2.3-2.7

---

## 1. Migration Purpose

Migration 002 creates the **pipeline data layer** — the tables that represent ChronoArb's core value chain from raw source observation through normalized listing, duplicate detection, valuation, and opportunity publication. These 8 tables are the heart of the system: they store every listing the platform ingests, every valuation it computes, and every opportunity it surfaces to dealers.

This migration depends on 001 (identity + catalog) because:
- `raw_snapshots` references `sources` (from 001)
- `normalized_listings` references `references` and `parsed_listings`
- `opportunities` references `organizations` (from 001) and `valuations`
- `opportunity_views` references `users` (from 001)

---

## 2. Tables Created

| # | Table | Domain | Record Count (MVP est.) |
|---|-------|--------|------------------------|
| 10 | `raw_snapshots` | Evidence | ~10K/month (3 sources × daily scans) |
| 11 | `parsed_listings` | Parsing | 1:1 with raw_snapshots |
| 12 | `normalized_listings` | Normalization | 1:1 with parsed_listings |
| 13 | `duplicate_groups` | Duplicates | ~500 groups |
| 14 | `duplicate_group_members` | Duplicates | ~1:3 ratio (listings per group) |
| 15 | `valuations` | Valuation | 1:1 with normalized_listings |
| 16 | `opportunities` | Opportunities | ~500 published, ~2K total (across material versions) |
| 17 | `opportunity_views` | Analytics | ~1K/month |

---

## 3. Dependency Order (Creation Sequence)

Tables must be created in this exact order to satisfy foreign key relationships:

```
10. raw_snapshots              ← FK → sources (001, table 6)
11. parsed_listings            ← FK → raw_snapshots (002, table 10)
12. normalized_listings        ← FK → parsed_listings (002, table 11), FK → references (001, table 5)
13. duplicate_groups           ← FK → normalized_listings (002, table 12)
14. duplicate_group_members    ← FK → duplicate_groups (002, table 13), FK → normalized_listings (002, table 12)
15. valuations                 ← FK → normalized_listings (002, table 12)
16. opportunities              ← FK → organizations (001, table 1), FK → normalized_listings (002, table 12), FK → valuations (002, table 15)
17. opportunity_views          ← FK → opportunities (002, table 16), FK → users (001, table 2)
```

**Downgrade order:** 17 → 10 (reverse of creation).

---

## 4. ENUM Requirements

Two PostgreSQL native ENUMs must be created BEFORE the tables that reference them:

| ENUM | Values | Used By | Created Before |
|------|--------|---------|---------------|
| `listing_status` | `active`, `quarantined`, `suppressed`, `stale` | `normalized_listings.status` | Table 12 |
| `opportunity_state` | `published`, `dismissed`, `contacted`, `purchased`, `expired` | `opportunities.state` | Table 16 |

**Creation pattern:**
```python
op.execute("CREATE TYPE listing_status AS ENUM ('active', 'quarantined', 'suppressed', 'stale')")
op.execute("CREATE TYPE opportunity_state AS ENUM ('published', 'dismissed', 'contacted', 'purchased', 'expired')")
```

**Drop pattern (downgrade):**
```python
op.execute("DROP TYPE opportunity_state")
op.execute("DROP TYPE listing_status")
```

Use `create_type=False` on the `sa.Column(..., postgresql.ENUM(..., create_type=False))` to prevent Alembic from auto-creating the type (it's already created manually).

---

## 5. Foreign Key Ordering

| Table | FK Count | FK Target Tables |
|-------|----------|-----------------|
| `raw_snapshots` | 1 | `sources(id)` |
| `parsed_listings` | 1 | `raw_snapshots(id)` — UNIQUE (1:1 relationship) |
| `normalized_listings` | 2 | `parsed_listings(id)` UNIQUE, `references(id)` |
| `duplicate_groups` | 1 | `normalized_listings(id)` — representative |
| `duplicate_group_members` | 2 | `duplicate_groups(id)`, `normalized_listings(id)` |
| `valuations` | 1 | `normalized_listings(id)` |
| `opportunities` | 3 | `organizations(id)`, `normalized_listings(id)`, `valuations(id)` |
| `opportunity_views` | 2 | `opportunities(id)`, `users(id)` |

**FK naming convention:** `fk_{table}_{referenced_column_name}` (or `fk_{table}_{purpose}` for multi-FK tables).

Examples:
- `fk_raw_snapshots_source_id`
- `fk_normalized_listings_parsed_listing_id`
- `fk_normalized_listings_reference_id`
- `fk_opportunities_organization_id`
- `fk_opportunities_listing_id`
- `fk_opportunities_valuation_id`

---

## 6. Constraints

### Table 10: raw_snapshots

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_raw_snapshots` |
| `source_id` | `TEXT` | NOT NULL, FK → `sources(id)` |
| `external_id` | `TEXT` | NOT NULL |
| `adapter_version` | `TEXT` | NOT NULL |
| `checksum` | `TEXT` | NOT NULL |
| `raw_payload` | `JSONB` | Nullable (unparsed or referenced in S3) |
| `fetched_at` | `TIMESTAMPTZ` | Nullable |
| | | UNIQUE `uq_raw_snapshots` on `(source_id, external_id, adapter_version, checksum)` |

**Business purpose:** Immutable evidence storage. Each row is a single observation from a source at a point in time. The composite UNIQUE prevents duplicate storage of identical evidence. `checksum` is a content hash of the raw response — identical content + same parser version = same snapshot.

---

### Table 11: parsed_listings

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_parsed_listings` |
| `snapshot_id` | `TEXT` | NOT NULL, UNIQUE, FK → `raw_snapshots(id)` |
| `parser_version` | `TEXT` | NOT NULL |
| `listing_price` | `NUMERIC(18,2)` | Nullable (some listings lack price) |
| `price_currency` | `CHAR(3)` | Nullable |
| `listing_title` | `TEXT` | Nullable |
| `description` | `TEXT` | Nullable |
| `parsed_attributes` | `JSONB` | Nullable (condition_text, set_info, year, location, seller_name) |
| `external_url` | `TEXT` | Nullable |
| `listed_at` | `TIMESTAMPTZ` | Nullable |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |

**Business purpose:** Structured extract of a raw snapshot. The parser version is recorded so that future parser upgrades don't invalidate historical parsed listings. The 1:1 relationship with raw_snapshots (enforced by UNIQUE FK) means one snapshot produces exactly one parsed listing.

**Money note:** `listing_price` is the price AS ADVERTISED by the source, in the source's currency. It is NOT an acquisition cost — that is computed during valuation. This is raw data.

---

### Table 12: normalized_listings

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_normalized_listings` |
| `parsed_listing_id` | `TEXT` | NOT NULL, UNIQUE, FK → `parsed_listings(id)` |
| `reference_id` | `TEXT` | NOT NULL, FK → `references(id)` |
| `normalization_version` | `TEXT` | NOT NULL |
| `match_confidence` | `NUMERIC(5,4)` | Nullable (0.0–1.0) |
| `match_method` | `TEXT` | Nullable (exact, alias, variant_rule, classifier) |
| `match_features` | `JSONB` | Nullable |
| `condition` | `TEXT` | Nullable (new, pre_owned, unknown) |
| `set_status` | `TEXT` | Nullable (full_set, box_only, watch_only, unknown) |
| `seller_geography` | `TEXT` | Nullable |
| `normalized_price` | `NUMERIC(18,2)` | Nullable (in base currency) |
| `normalized_currency` | `CHAR(3)` | Nullable |
| `fx_rate` | `NUMERIC(18,8)` | NOT NULL **(ADR-0005 D1)** |
| `fx_source` | `TEXT` | NOT NULL **(ADR-0005 D1)** |
| `fx_date` | `DATE` | NOT NULL **(ADR-0005 D1)** |
| `observation_at` | `TIMESTAMPTZ` | NOT NULL **(ADR-0004 D1)** |
| `status` | `listing_status` | NOT NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |

**Business purpose:** The canonical representation of a listing — linked to a watch reference, with currency-normalized price, match confidence, and source attribution. This is the table that feeds the valuation engine.

**ADR corrections:**
- `observation_at` (ADR-0004): When the listing was observed at the source. Populated at normalization time as `COALESCE(parsed_listings.listed_at, raw_snapshots.fetched_at)`. Enables data age calculation in customer-facing estimates.
- `fx_source` (ADR-0005): Which provider supplied the exchange rate (e.g., "ecb", "openexchange"). Enables FX rate auditability.
- `fx_date` (ADR-0005): Date the rate was valid for. Enables reproducibility.

**Status semantics:**
- `active`: Currently listed, valid for valuation
- `quarantined`: Suspicious/ambiguous — held for operations review
- `suppressed`: Deliberately hidden (duplicate, spam, error)
- `stale`: Not seen in recent source scans — may no longer be available

---

### Table 13: duplicate_groups

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_duplicate_groups` |
| `model_version` | `TEXT` | NOT NULL |
| `representative_id` | `TEXT` | NOT NULL, FK → `normalized_listings(id)` |
| `method` | `TEXT` | Nullable |
| `confidence` | `NUMERIC(5,4)` | Nullable |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |

**Business purpose:** Groups multiple normalized listings that represent the same underlying listing (same watch from same seller listed on multiple sources, or re-listed). The `representative_id` points to the best/most-complete listing in the group. `model_version` enables re-running duplicate detection with improved models.

---

### Table 14: duplicate_group_members

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_duplicate_group_members` |
| `group_id` | `TEXT` | NOT NULL, FK → `duplicate_groups(id)` |
| `listing_id` | `TEXT` | NOT NULL, FK → `normalized_listings(id)` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |
| | | UNIQUE `uq_duplicate_group_members` on `(group_id, listing_id)` |

**Business purpose:** Many-to-many relationship between duplicate_groups and normalized_listings. Prevents the same listing from being in the same group twice (UNIQUE constraint). Note: a listing can be in multiple groups across different duplicate detection runs (different `model_version` values on groups).

---

### Table 15: valuations

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_valuations` |
| `listing_id` | `TEXT` | NOT NULL, FK → `normalized_listings(id)` |
| `model_version` | `TEXT` | NOT NULL |
| `config_version` | `TEXT` | NOT NULL |
| `cost_assumptions_version` | `TEXT` | NOT NULL |
| `expected_exit_price` | `NUMERIC(18,2)` | Nullable |
| `exit_price_currency` | `CHAR(3)` | Nullable |
| `all_in_acquisition` | `NUMERIC(18,2)` | Nullable |
| `expected_net_resale` | `NUMERIC(18,2)` | Nullable |
| `expected_net_profit` | `NUMERIC(18,2)` | Nullable |
| `roi` | `NUMERIC(10,6)` | Nullable |
| `low_estimate` | `NUMERIC(18,2)` | Nullable |
| `high_estimate` | `NUMERIC(18,2)` | Nullable |
| `confidence` | `NUMERIC(5,4)` | Nullable |
| `comparable_count` | `INT` | Nullable |
| `sample_dispersion` | `NUMERIC(10,4)` | Nullable |
| `adjustment_details` | `JSONB` | Nullable |
| `risk_reserve_details` | `JSONB` | Nullable |
| `cost_breakdown` | `JSONB` | Nullable |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |

**Business purpose:** The computed financial analysis for a listing. This is the output of the valuation engine — the "should I buy this watch?" answer expressed as numbers.

**Financial columns (all DECIMAL, no float):**
- `expected_exit_price`: What the watch is estimated to sell for at resale
- `all_in_acquisition`: Total cost to acquire (listing_price + buyer_fee + tax_and_duty + inbound_shipping + authentication_cost + service_reserve + financing_cost + acquisition_risk_reserve)
- `expected_net_resale`: Net proceeds from resale (expected_exit_price - selling_fee - outbound_shipping - resale_payment_cost - exit_risk_reserve)
- `expected_net_profit`: `expected_net_resale - all_in_acquisition`
- `roi`: `expected_net_profit / all_in_acquisition`

**Version tracking:** `model_version`, `config_version`, and `cost_assumptions_version` record exactly which valuation model, configuration, and cost assumptions produced this analysis. Enables full reproducibility and comparison across model versions.

---

### Table 16: opportunities

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_opportunities` |
| `organization_id` | `TEXT` | NOT NULL, FK → `organizations(id)` |
| `listing_id` | `TEXT` | NOT NULL, FK → `normalized_listings(id)` |
| `valuation_id` | `TEXT` | NOT NULL, FK → `valuations(id)` |
| `material_version` | `INT` | NOT NULL |
| `score` | `NUMERIC(10,4)` | Nullable |
| `state` | `opportunity_state` | NOT NULL |
| `positive_factors` | `JSONB` | Nullable |
| `negative_factors` | `JSONB` | Nullable |
| `published_at` | `TIMESTAMPTZ` | Nullable |
| `state_changed_at` | `TIMESTAMPTZ` | Nullable |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() |
| | | UNIQUE `uq_opportunities_org_listing_version` on `(organization_id, listing_id, material_version)` |

**Business purpose:** A potentially profitable listing surfaced to a specific organization. Opportunities are **tenant-scoped** — the same listing may produce different opportunities for different organizations because cost assumptions (fees, shipping, taxes) vary by organization.

**State machine:**
```
(published) ──► dismissed
    │              (dealer dismissed)
    ├──► contacted
    │     (dealer contacted seller)
    ├──► purchased
    │     (dealer bought the watch)
    └──► expired
          (listing no longer available)
```

**Initial state:** Opportunities are created in `published` state by the alert matching worker. There is no `draft` or `pending` transient state — an opportunity either exists (published) or has been acted upon (dismissed/contacted/purchased/expired). The `published_at` timestamp is set to `NOW()` at creation time. The migration schema enforces `state NOT NULL` via the `opportunity_state` ENUM column — every opportunity row must have an explicit state at INSERT time.

**Material version:** Every time the underlying listing or valuation changes (price drop, new comparable, model recalibration), the opportunity's `material_version` increments. The UNIQUE constraint on `(org_id, listing_id, material_version)` ensures one opportunity per listing per version per org. Historical versions are preserved (immutable records per ADR-0001 D10).

**Score:** Computed from expected_net_profit, ROI, confidence, data age, and reference liquidity. Higher score = better opportunity.

---

### Table 17: opportunity_views

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `TEXT` | PRIMARY KEY `pk_opportunity_views` |
| `opportunity_id` | `TEXT` | NOT NULL, FK → `opportunities(id)` |
| `user_id` | `TEXT` | NOT NULL, FK → `users(id)` |
| `viewed_at` | `TIMESTAMPTZ` | Nullable |
| | | UNIQUE `uq_opportunity_views` on `(opportunity_id, user_id)` |

**Business purpose:** Records that a specific user viewed a specific opportunity. Used for analytics (view-to-action conversion rates) and UI (marking opportunities as "seen"). The UNIQUE constraint ensures one view record per user per opportunity — repeat views update `viewed_at` (handled at the application level, not in schema).

---

## 7. Indexes

Indexes are created in migration 004 (not inline with table creation). However, the following indexes WILL apply to these tables — they are documented here for awareness when writing the migration:

| Index | Table | Purpose |
|-------|-------|---------|
| `idx_opportunities_org_state` | opportunities | Feed queries: filter by org + state, sorted by published_at |
| `idx_opportunities_published` | opportunities | Partial index: only published opportunities |
| `idx_normalized_listings_ref` | normalized_listings | Catalog queries: find listings by reference |
| `idx_normalized_listings_active` | normalized_listings | Partial index: only active listings for alert matching |

**No indexes are created in migration 002.** Migration 004 adds all indexes after all 25 tables exist.

---

## 8. Upgrade Verification

After applying migration 002 (on top of 001):

```bash
# Table count — 17 total (9 from 001 + 8 from 002)
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\dt" | wc -l
# Expected: 18 (17 tables + header)

# ENUM verification
docker exec chronoarb-pg psql -U postgres -d chronoarb -c \
  "SELECT typname FROM pg_type WHERE typtype='e' ORDER BY typname;"
# Expected:
#   listing_status
#   membership_role
#   opportunity_state

# ADR correction verification — normalized_listings
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d normalized_listings"
# Must show:
#   observation_at   | timestamp with time zone | not null
#   fx_source        | text                     | not null
#   fx_date          | date                     | not null

# Money column verification — valuations
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d valuations"
# Must show NUMERIC types for: expected_exit_price, all_in_acquisition,
# expected_net_resale, expected_net_profit, roi, low_estimate, high_estimate

# FK verification — opportunities
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d opportunities"
# Must show 3 foreign keys: organization_id, listing_id, valuation_id
# Must show UNIQUE constraint on (organization_id, listing_id, material_version)

# FK verification — normalized_listings
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d normalized_listings"
# Must show FK to parsed_listings (UNIQUE) and references
# Must show UNIQUE constraint on parsed_listing_id

# FK verification — raw_snapshots
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\d raw_snapshots"
# Must show FK to sources
# Must show UNIQUE constraint on (source_id, external_id, adapter_version, checksum)
```

---

## 9. Downgrade Verification

After downgrading migration 002:

```bash
# Table count — back to 9 (001 only)
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\dt" | wc -l
# Expected: 10 (9 tables + header)

# ENUM verification — listing_status and opportunity_state are gone
docker exec chronoarb-pg psql -U postgres -d chronoarb -c \
  "SELECT typname FROM pg_type WHERE typtype='e';"
# Expected: membership_role (only — from 001)

# Verify no tables from 002 remain
docker exec chronoarb-pg psql -U postgres -d chronoarb -c \
  "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN 
   ('raw_snapshots','parsed_listings','normalized_listings','duplicate_groups',
    'duplicate_group_members','valuations','opportunities','opportunity_views');"
# Expected: (0 rows)
```

---

## 10. Data Integrity Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **1:1 UNIQUE FK vs regular FK on parsed_listings → raw_snapshots** | NOTE | The `snapshot_id` FK on `parsed_listings` is UNIQUE, enforcing a 1:1 relationship. If a snapshot is parsed twice (e.g., parser upgrade), the INSERT fails. The application must handle this by creating a NEW snapshot for re-parsing (different checksum) or by not re-parsing existing snapshots. This behavior is correct per the design — a snapshot is parsed once with a specific parser version. |
| **NUMERIC(18,2) for prices with currencies in CHF/JPY/KRW** | MINOR | `NUMERIC(18,2)` can represent values up to 10^16 with 2 decimal places. This is sufficient for watches (max listing ~$10M = 10^7, well within range). Non-JPY currencies use 2 decimal places. JPY uses 0 decimal places — the `CHAR(3)` currency code identifies which convention applies. No schema change needed. |
| **expected_net_profit can be negative** | NOTE | `NUMERIC(18,2)` supports negative values. An opportunity with negative profit may still be useful to store for learning purposes (the dealer dismissed it for the right reason). No CHECK constraint restricting profit to positive values. |
| **material_version as INT vs SMALLINT** | NOTE | Using `INT` (4 bytes, range ±2B). For MVP with manual material version incrementing, this is massively over-provisioned. Could use `SMALLINT` (2 bytes, range ±32K) for space efficiency. Decision: keep `INT` — the space difference is negligible (<1MB per 100K rows) and `INT` prevents overflow if the version increments frequently during initial pipeline development. |
| **observation_at has no default** | NOTE | `observation_at TIMESTAMPTZ NOT NULL` with no `DEFAULT`. The normalization worker MUST populate this field. If a bug causes NULL to be inserted, PostgreSQL rejects the row. This is intentional — forces the worker to always provide the observation time. |
| **opportunity_views uses viewed_at only** | NOTE | Opportunity_views has a `viewed_at TIMESTAMPTZ` column but no separate `created_at`. This is by design — the view record is created with `viewed_at = NOW()`, and subsequent views update `viewed_at`. The row creation time is identical to the first view time. No separate `created_at` needed. |

---

## 11. Re-Upgrade Idempotency

If migration 002 is reapplied (after downgrade), it must produce identical results:

```bash
make db-reset            # downgrade base + re-upgrade (applies 001)
make db-migrate          # applies 002
# Verify 17 tables
make db-rollback         # downgrade 002 → back to 001 state
make db-migrate          # re-apply 002
# Verify 17 tables (identical state)
```

The upgrade must be idempotent: running it twice should not error (Alembic tracks applied revisions via `alembic_version` table).

---

## 12. Table Summary

| Table | Columns | PK | FKs | UNIQUEs | ENUMs | Money Columns |
|-------|---------|----|-----|---------|-------|---------------|
| `raw_snapshots` | 7 | 1 | 1 | 1 | 0 | 0 |
| `parsed_listings` | 11 | 1 | 1 | 1 | 0 | 1 |
| `normalized_listings` | 18 | 1 | 2 | 1 | 1 | 2 |
| `duplicate_groups` | 6 | 1 | 1 | 0 | 0 | 0 |
| `duplicate_group_members` | 4 | 1 | 2 | 1 | 0 | 0 |
| `valuations` | 20 | 1 | 1 | 0 | 0 | 8 |
| `opportunities` | 13 | 1 | 3 | 1 | 1 | 1 |
| `opportunity_views` | 4 | 1 | 2 | 1 | 0 | 0 |
| **Totals** | **83** | **8** | **13** | **6** | **2** | **12** |
