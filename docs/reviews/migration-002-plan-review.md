# Migration 002 — Plan Review

**Review type:** Pre-implementation schema audit
**Reviewed document:** docs/implementation/migration-002-plan.md
**Date:** 2026-08-03T16:30:50+05:00
**Reviewer:** Architecture review pass
**Cross-referenced:** database-design.md §2.3-2.7, ADR-0004, ADR-0005, ADR-0008

---

## Executive Summary

The migration 002 plan is technically sound across all 10 review dimensions. Table ordering satisfies all FK dependencies. Financial columns use correct NUMERIC types. ADR corrections (observation_at, fx_source, fx_date) are accurately encoded. Two minor issues need clarification: a column count discrepancy in the summary table, and the unspecified initial state for opportunities. Neither blocks implementation.

**Verdict: READY FOR IMPLEMENTATION**

---

## 1. Table Dependency Ordering

### Verification

| Child Table | FK Target | Target Migration | Satisfied? |
|-------------|-----------|-----------------|------------|
| `raw_snapshots` | `sources` | 001 (table 6) | YES |
| `parsed_listings` | `raw_snapshots` | 002 (table 10) | YES |
| `normalized_listings` | `parsed_listings` | 002 (table 11) | YES |
| `normalized_listings` | `references` | 001 (table 5) | YES |
| `duplicate_groups` | `normalized_listings` | 002 (table 12) | YES |
| `duplicate_group_members` | `duplicate_groups` | 002 (table 13) | YES |
| `duplicate_group_members` | `normalized_listings` | 002 (table 12) | YES |
| `valuations` | `normalized_listings` | 002 (table 12) | YES |
| `opportunities` | `organizations` | 001 (table 1) | YES |
| `opportunities` | `normalized_listings` | 002 (table 12) | YES |
| `opportunities` | `valuations` | 002 (table 15) | YES |
| `opportunity_views` | `opportunities` | 002 (table 16) | YES |
| `opportunity_views` | `users` | 001 (table 2) | YES |

**Finding:** All 13 foreign keys reference tables that exist when their parent table is created. Zero circular dependencies. Creation order (10→17) is correct. Downgrade order (17→10) is correct.

**PASS.**

---

## 2. Financial Column Correctness

### Cross-reference against database-design.md

| Table | Column | Plan Type | Design Spec | Match? |
|-------|--------|-----------|-------------|--------|
| `parsed_listings` | `listing_price` | `NUMERIC(18,2)` | `NUMERIC(18,2)` | YES |
| `normalized_listings` | `normalized_price` | `NUMERIC(18,2)` | `NUMERIC(18,2)` | YES |
| `normalized_listings` | `fx_rate` | `NUMERIC(18,8)` | `NUMERIC(18,8)` | YES |
| `valuations` | `expected_exit_price` | `NUMERIC(18,2)` | `NUMERIC(18,2)` | YES |
| `valuations` | `all_in_acquisition` | `NUMERIC(18,2)` | `NUMERIC(18,2)` | YES |
| `valuations` | `expected_net_resale` | `NUMERIC(18,2)` | `NUMERIC(18,2)` | YES |
| `valuations` | `expected_net_profit` | `NUMERIC(18,2)` | `NUMERIC(18,2)` | YES |
| `valuations` | `roi` | `NUMERIC(10,6)` | `NUMERIC(10,6)` | YES |
| `valuations` | `low_estimate` | `NUMERIC(18,2)` | `NUMERIC(18,2)` | YES |
| `valuations` | `high_estimate` | `NUMERIC(18,2)` | `NUMERIC(18,2)` | YES |
| `opportunities` | `score` | `NUMERIC(10,4)` | `NUMERIC(10,4)` | YES |

**Finding:** All 11 financial columns match database-design.md specifications. No drift. AGENTS.md §2 Decimal-only requirement is enforced at the schema level via NUMERIC types. Application-level decimal enforcement is handled by the `Money` domain value object (implemented in Batch 2).

**PASS.**

---

## 3. NUMERIC Precision Decisions

### Precision analysis

| Precision | Columns | Use Case | Assessment |
|-----------|---------|----------|------------|
| `(18,2)` | Listing prices, acquisition costs, resale values, profit | Currency amounts up to $10^16 with cent precision | PASS — 100x headroom above max watch price (~$10M) |
| `(10,6)` | ROI | Ratio like 0.041667 (4.1667%) | PASS — 4 integer + 6 fractional digits |
| `(10,4)` | Score, sample_dispersion | Weighted scores, statistical metrics | PASS — appropriate precision |
| `(5,4)` | Confidence, match_confidence | 0.0000–1.0000 range | PASS — exact fit for probability |
| `(18,8)` | FX rates | 1.08500000 (EUR/USD) | PASS — 8 decimal places for FX rate precision |

**Finding:** All precision choices are appropriate. The `(18,2)` choice for currency adequately covers watch prices (highest known watch sale ~$31M, well within 10^16). The `(18,8)` for FX rates enables sub-pip precision for all major currency pairs. `(10,6)` for ROI enables percentage with 6 decimal places (0.000001 = 0.0001%).

**PASS.**

---

## 4. FX Lineage Compliance (ADR-0005)

### ADR-0005 D1 Requirements

| Requirement | Column | Plan Implementation | Status |
|-------------|--------|--------------------|--------|
| FX rate value | `fx_rate NUMERIC(18,8) NOT NULL` | Line 164 | PASS |
| FX rate source | `fx_source TEXT NOT NULL` | Line 165 | PASS |
| FX rate date | `fx_date DATE NOT NULL` | Line 166 | PASS |
| All three NOT NULL | Migration enforces at schema level | Lines 164-166 | PASS |

**ADR-0005 D2** (use a single named provider) and **D3** (store rate not calculation) are application-layer concerns — not migration concerns. They are correctly deferred to the normalization worker implementation.

**Finding:** All three ADR-0005 D1 requirements are encoded in the migration schema. Full FX rate provenance is enforceable at the database level.

**PASS.**

---

## 5. Observation Timestamp Correctness (ADR-0004)

### ADR-0004 D1 Requirements

| Requirement | Plan Implementation | Status |
|-------------|--------------------|--------|
| `observation_at TIMESTAMPTZ NOT NULL` | Line 167 | PASS |
| No DEFAULT — worker MUST populate | Line 399 | PASS (by design) |
| Populated as `COALESCE(listed_at, fetched_at)` | Line 174 | PASS (documented as worker concern) |

**ADR-0004 D2** (compute data_age in API layer) is correctly identified as an API-layer concern, not a migration concern.

**ADR-0004 D3** (include all four fields in API responses) is correctly deferred to API implementation.

**Finding:** The schema correctly encodes ADR-0004 D1. The `NOT NULL` constraint without a default forces the normalization worker to always provide the observation timestamp — a design choice that prevents silent NULLs in critical data.

**PASS.**

---

## 6. Tenant Isolation

### Tenant-Scoped Tables in Migration 002

| Table | Has `organization_id`? | Assessment |
|-------|------------------------|------------|
| `raw_snapshots` | No | Correct — global evidence, not tenant-specific |
| `parsed_listings` | No | Correct — global parsed data |
| `normalized_listings` | No | Correct — global canonical listings |
| `duplicate_groups` | No | Correct — global duplicate detection |
| `duplicate_group_members` | No | Correct — global |
| `valuations` | No | Correct — global; results are shared, opportunity publication is tenant-scoped |
| `opportunities` | **Yes** (`NOT NULL`, FK → organizations) | Correct — opportunities are tenant-scoped per ADR-0001 D7 |
| `opportunity_views` | No | Correct — views are user-scoped, not org-scoped; org can be derived via `opportunities.organization_id` |

**Finding:** Only `opportunities` carries `organization_id`. This is correct — the pipeline (raw→parsed→normalized→valued) produces global data. Tenant scoping happens at the opportunity level, where cost assumptions, fees, and taxes vary by organization.

**PASS.**

---

## 7. Opportunity Versioning

### ADR-0001 D10 Immutable Records

| Requirement | Implementation | Status |
|-------------|---------------|--------|
| `material_version INT NOT NULL` | Line 261 | PASS |
| UNIQUE `(org_id, listing_id, material_version)` | Line 269 | PASS |
| Historical versions preserved | Plan §6 business purpose note | PASS |
| No UPDATE on published opportunities | Implicit — new version = new row | PASS |

### Opportunity Initial State

**Issue CR-01: Unspecified initial state for opportunities.** (MINOR)

The plan documents the state machine transitions (published → dismissed/contacted/purchased/expired) but does not specify what state an opportunity is CREATED in. The alert matcher worker creates opportunities — should they be `published` directly, or created as some transient state first?

The ENUM `opportunity_state` has no `draft` or `pending` value. This implies opportunities are created directly in `published` state. This is valid but should be documented explicitly in the plan.

**Action:** Add to §6 (Table 16 business purpose): "Opportunities are created in `published` state by the alert matching worker. The `published_at` timestamp is set at creation time."

**CR-01 does not block migration implementation** — it is a documentation gap, not a schema gap.

**PASS (with MINOR documentation note).**

---

## 8. Foreign Key Safety

### ON DELETE Behavior

The plan does not specify `ON DELETE` behavior for foreign keys. Database-design.md does not specify it either. This is acceptable — the default PostgreSQL behavior for unqualified FKs is `NO ACTION` (prevent deletion of referenced rows).

| FK | ON DELETE Default | Behavior | Acceptable? |
|----|-------------------|----------|-------------|
| All 13 FKs | `NO ACTION` (default) | Cannot delete a `sources` row if `raw_snapshots` reference it | YES — prevents orphan data |

### Deferred FK Considerations

None of the FKs need `DEFERRABLE` — the creation order satisfies all constraints at insertion time, and the downgrade order satisfies all constraints at deletion time.

### CASCADE Analysis

Using `CASCADE` would be dangerous: deleting a `source` would cascade-delete all raw_snapshots, parsed_listings, normalized_listings, etc. Default `NO ACTION` is the correct choice for a pipeline data store.

**Finding:** All FKs are safe. Default `NO ACTION` behavior is correct for a pipeline data store where referential integrity should be enforced, not silently cascaded.

**PASS.**

---

## 9. ENUM Lifecycle

### Creation Timing

| ENUM | Created | Before Table | Table Created |
|------|---------|-------------|---------------|
| `listing_status` | lines 63-69 | Table 12 (`normalized_listings`) | Table 12 uses `listing_status` column |
| `opportunity_state` | lines 63-69 | Table 16 (`opportunities`) | Table 16 uses `opportunity_state` column |

Both ENUMs are created at the start of `upgrade()` — this is correct.

### Drop Timing

| ENUM | Dropped After | Order Correct? |
|------|--------------|---------------|
| `opportunity_state` | Table 16 (`opportunities`) | YES — used by table 16 |
| `listing_status` | Table 12 (`normalized_listings`) | YES — used by table 12 |

### CREATE OR REPLACE Risk

The plan does not use `CREATE TYPE IF NOT EXISTS` — this is correct. The migration is the first time these types are created (no prior migration creates them). Adding `IF NOT EXISTS` would mask errors if the type already exists unexpectedly.

### `create_type=False`

The plan specifies `create_type=False` on ENUM column definitions (line 78). This prevents Alembic from emitting an extra `CREATE TYPE` for each ENUM column, which would fail because the type already exists. This is the correct Alembic 2.0 pattern for hand-created ENUMs.

**Finding:** ENUM lifecycle is correctly managed. Both types are created before their consuming tables and dropped after. No temporal gaps.

**PASS.**

---

## 10. Downgrade Safety

### Table Drop Order Verification

| Drop Order | Table | FKs To | Satisfied? |
|------------|-------|--------|------------|
| 1st | `opportunity_views` | opportunities, users | YES — no child tables depend on it |
| 2nd | `opportunities` | organizations, normalized_listings, valuations | YES — opportunity_views already dropped |
| 3rd | `valuations` | normalized_listings | YES — opportunities already dropped |
| 4th | `duplicate_group_members` | duplicate_groups, normalized_listings | YES — no children |
| 5th | `duplicate_groups` | normalized_listings | YES — duplicate_group_members already dropped |
| 6th | `normalized_listings` | parsed_listings, references | YES — duplicate_groups, duplicate_group_members, valuations, opportunities already dropped |
| 7th | `parsed_listings` | raw_snapshots | YES — normalized_listings already dropped |
| 8th | `raw_snapshots` | sources | YES — parsed_listings already dropped |

### ENUM Drop Order

| Drop Order | ENUM | After Table | Correct? |
|------------|------|------------|----------|
| 9th | `opportunity_state` | opportunities (2nd) | YES |
| 10th | `listing_status` | normalized_listings (6th) | YES |

**Finding:** Full downgrade is safe. All child tables are dropped before their parents. All ENUMs are dropped after their consuming tables. The downgrade can be executed without constraint violations.

**PASS.**

---

## 11. Additional Findings

### Issue CR-02: Column count discrepancy for valuations in summary table. (MINOR)

The plan's §12 summary table reports `valuations` as having 19 columns, but counting from §6 (lines 217-238) shows 20 columns:

```text
§6 listing:  id, listing_id, model_version, config_version, cost_assumptions_version,
             expected_exit_price, exit_price_currency, all_in_acquisition,
             expected_net_resale, expected_net_profit, roi, low_estimate,
             high_estimate, confidence, comparable_count, sample_dispersion,
             adjustment_details, risk_reserve_details, cost_breakdown, created_at
             = 20 columns

§12 summary: 19 columns ← off by 1
```

**Action:** Update §12 summary to show 20 columns for valuation. Total columns row changes from 83 to 84.

**CR-02 does not block migration implementation** — the §6 specification is correct and will be used for migration authoring, not the §12 summary.

### Issue CR-03: The plan uses the term `created_at` for `opportunity_views` in the data integrity section but the schema uses `viewed_at`. (NOTE)

The §10 data integrity risk table says "opportunity_views.created_at vs viewed_at" as a NOTE, but `created_at` does not exist on `opportunity_views`. The text correctly states the design intent (viewed_at serves as creation timestamp), but the heading text is misleading.

**Action:** Reword the risk cell to: "opportunity_views has `viewed_at` but no separate `created_at`." Immediate fix — 30 seconds.

### Count verification: raw_snapshots column count

§12 summary says `raw_snapshots` has 8 columns. Let me verify from §6:
- id, source_id, external_id, adapter_version, checksum, raw_payload, fetched_at = 7 columns
- Plus: the UNIQUE constraint is not a column

Wait — the table has 7 data columns + 1 PK. But the §6 table listing shows 7 rows plus a constraint row. The plan might be counting the id column separately from the data columns. Let me count:
1. id
2. source_id
3. external_id
4. adapter_version
5. checksum
6. raw_payload
7. fetched_at
= 7 columns

But the summary says 8. There's no hidden column. This is another off-by-1.

Actually, looking more carefully: does `raw_snapshots` have a `created_at` column? Looking at database-design.md §2.3:
```
raw_snapshots
├── id (PK)            ULID
├── source_id          FK → sources.id
├── external_id        TEXT NOT NULL
├── adapter_version    TEXT NOT NULL
├── checksum           TEXT NOT NULL
├── raw_payload        JSONB
├── fetched_at         TIMESTAMPTZ
└── UNIQUE(source_id, external_id, adapter_version, checksum)
```

7 columns listed. No `created_at`. The plan's §6 also shows 7 columns (id, source_id, external_id, adapter_version, checksum, raw_payload, fetched_at). But the §12 summary says 8. This is a plan bug.

**Finding:** §12 summary off by 1 for both raw_snapshots (8→7) and valuations (19→20). Total should be 82, not 83, after fixing both. (Actually, raw_snapshots is 7 and valuations is 20, so total = 7 + 11 + 18 + 6 + 4 + 20 + 13 + 4 = 83. Wait, let me recalculate: 7 + 11 + 18 + 6 + 4 + 20 + 13 + 4 = 83. So removing 1 from raw_snapshots (8→7) and adding 1 to valuations (19→20) keeps the total at 83. Actually no — the plan has 8 for raw_snapshots (wrong, should be 7) and 19 for valuations (wrong, should be 20). So the total of 83 remains the same by coincidence: (8-1) + (19+1) = 8 + 19 = 27 for those two, same as 7+20=27. The total remains 83.)

### CR-02b: raw_snapshots column count off by 1 in summary

Similarly, raw_snapshots in §12 is 8 but §6 shows 7 columns. Together with valuations (19→20), total remains 83 by coincidence.

Both are MINOR — the §6 specifications are authoritative and will be used for migration authoring. The §12 summary table is documentation only.

**PASS (with MINOR summary corrections).**

---

## 12. Correction Summary

| ID | Severity | Description | Location | Action |
|----|----------|-------------|----------|--------|
| CR-01 | MINOR | Unspecified opportunity initial state | Plan §6, Table 16 | Add: "Opportunities are created in `published` state by the alert matcher." |
| CR-02 | MINOR | valuations column count: §6 shows 20, §12 shows 19 | Plan §12 | Change 19→20 in summary |
| CR-02b | MINOR | raw_snapshots column count: §6 shows 7, §12 shows 8 | Plan §12 | Change 8→7 in summary |
| CR-03 | NOTE | Risk cell heading says "opportunity_views.created_at" but column doesn't exist | Plan §10 | Reword: "opportunity_views has `viewed_at` but no separate `created_at`" |

---

## 13. Batch Progression Gate

**Question: Is migration 002 ready for implementation?**

Yes. All 10 review dimensions pass at the schema level. The 4 corrections are documentation-only — §6 specifications are correct and will be used for migration authoring.

| Gate | Status |
|------|--------|
| Table dependency order correct | PASS |
| Financial columns use NUMERIC | PASS |
| NUMERIC precision matches design | PASS |
| ADR-0004 FX compliance | PASS |
| ADR-0005 observation_at compliance | PASS |
| Tenant isolation enforced | PASS |
| Opportunity versioning correct | PASS |
| FK safety (NO ACTION default) | PASS |
| ENUM lifecycle manageable | PASS |
| Downgrade safe | PASS |

**Verdict: READY FOR IMPLEMENTATION**

No schema change is needed. All findings are documentation corrections in the plan, not migration defects. Migration authoring can proceed directly from §6 (Table Specifications).
