# ChronoArb — Migration 004 Implementation Plan

**Plan type:** Migration authoring guide
**Migration:** 004_indexes
**Date:** 2026-08-03T17:15:46+05:00
**Status:** Ready for implementation
**References:** ADR-0008, database-design.md §3, ADR-0002

---

## 1. Purpose

Migration 004 creates all non-primary-key indexes across the 25 tables established by migrations 001–003. Indexes are isolated in a dedicated migration for three reasons:

1. **Index failures do not affect table data.** If an index DDL fails, tables remain intact — only that index fails. A failed `CREATE INDEX` in the same transaction as `CREATE TABLE` would roll back the table.
2. **Indexes are a performance concern, not a schema correctness concern.** The application works without indexes — it's just slower. Separating indexes from DDL makes this distinction explicit.
3. **Future index-only migrations can follow this pattern.** Adding an index to a production table via expand/contract uses a migration file that only contains `CREATE INDEX` / `DROP INDEX`, never table DDL.

---

## 2. Index Inventory

### 2.1 Included Indexes (12 total)

| # | Index Name | Table | Columns | Type | Reason |
|---|-----------|-------|---------|------|--------|
| 1 | `idx_memberships_org_user` | memberships | (organization_id, user_id) | B-tree | Lookup: "Is user X a member of organization Y?" — every auth middleware call |
| 2 | `idx_opportunities_org_state` | opportunities | (organization_id, state, published_at DESC) | B-tree | Feed: "All published opportunities for org Z, newest first" — primary dealer feed query |
| 3 | `idx_alert_rules_org` | alert_rules | (organization_id, is_enabled) | B-tree | Alert matching: "All enabled rules for org Z" — alert matcher startup and rule CRUD |
| 4 | `idx_feedbacks_org_opp` | feedbacks | (organization_id, opportunity_id) | B-tree | Activity feed: "All decisions for org Z on opportunity X" — activity timeline query |
| 5 | `idx_opportunities_published` | opportunities | (state, published_at DESC) **WHERE state = 'published'** | Partial | Feed (global): "All published opportunities, newest first" — smaller index (only published rows) |
| 6 | `idx_normalized_listings_ref` | normalized_listings | (reference_id, status, created_at DESC) | B-tree | Watch detail: "All active listings for reference X" — reference detail page |
| 7 | `idx_normalized_listings_active` | normalized_listings | (status, reference_id) **WHERE status = 'active'** | Partial | Alert matching: "Active listings for reference X" — alert matcher scans this |
| 8 | `idx_alert_deliveries_org_user` | alert_deliveries | (organization_id, user_id, created_at DESC) | B-tree | Delivery history: "All notifications for user U in org Z, newest first" |
| 9 | `idx_alert_deliveries_opp` | alert_deliveries | (opportunity_id, material_version) | B-tree | Alert re-delivery check: "Was this opportunity v3 already delivered?" |
| 10 | `idx_outbox_pending` | outbox_events | (status, created_at) **WHERE status = 'pending'** | Partial | Outbox worker: "Oldest pending events" — outbox worker poll loop |
| 11 | `idx_audit_org_time` | audit_events | (organization_id, created_at DESC) | B-tree | Audit browse: "All audit events for org Z, newest first" |
| 12 | `idx_audit_resource` | audit_events | (resource_type, resource_id) | B-tree | Audit resource lookup: "All changes to membership mem_X" |

### 2.2 Excluded Indexes (3 — redundant with UNIQUE constraints)

| Index Name | Column | Excluded Because |
|-----------|--------|-----------------|
| `idx_alert_deliveries_idem` | (idempotency_key) | `UNIQUE(idempotency_key)` already creates index `uq_alert_deliveries_idempotency_key` |
| `idx_feedbacks_idem` | (idempotency_key) | `UNIQUE(idempotency_key)` already creates index `uq_feedbacks_idempotency_key` |
| `idx_trade_outcomes_idem` | (idempotency_key) | `UNIQUE(idempotency_key)` already creates index `uq_trade_outcomes_idempotency_key` |

PostgreSQL automatically creates a B-tree index for every `UNIQUE` constraint. Creating a second index on the same column would:
- Waste disk space (duplicate index ~50% of table size per index)
- Slow down INSERTs (two indexes to update instead of one)
- Confuse `EXPLAIN` output (two identical indexes, planner picks one arbitrarily)

**Decision:** Exclude these 3 indexes. The database-design.md lists them, but they are redundant. This plan documents the exclusion as a deliberate deviation from database-design.md §3.

---

## 3. Index Detail

### Index 1: `idx_memberships_org_user`

| Property | Value |
|----------|-------|
| Table | `memberships` |
| Columns | (organization_id, user_id) |
| Type | B-tree (composite) |
| Alembic | `op.create_index("idx_memberships_org_user", "memberships", ["organization_id", "user_id"])` |

**Query:** `SELECT * FROM memberships WHERE organization_id = $1 AND user_id = $2`

This is the most-called query in the system — every authenticated API request resolves the user's membership to determine their role and organization context. The composite index enables a direct index scan without a sequential scan of the memberships table.

**Expected improvement:** Full table scan → single index lookup. At 1K memberships: ~1ms vs ~0.1ms. At 100K: ~50ms vs ~0.1ms.

---

### Index 2: `idx_opportunities_org_state`

| Property | Value |
|----------|-------|
| Table | `opportunities` |
| Columns | (organization_id, state, published_at DESC) |
| Type | B-tree (composite, descending) |
| Alembic | `op.create_index("idx_opportunities_org_state", "opportunities", ["organization_id", "state", sa.text("published_at DESC")])` |

**Query:** `SELECT * FROM opportunities WHERE organization_id = $1 AND state = $2 ORDER BY published_at DESC LIMIT 50`

This is the primary dealer feed query — "show me the latest 50 published opportunities for my org." The composite index covers filtering (org_id, state) and sorting (published_at DESC) in a single index scan, avoiding a file sort.

**Expected improvement:** Sequential scan + sort → index-only scan. At 10K opportunities: ~80ms → ~2ms.

---

### Index 3: `idx_alert_rules_org`

| Property | Value |
|----------|-------|
| Table | `alert_rules` |
| Columns | (organization_id, is_enabled) |
| Type | B-tree (composite) |
| Alembic | `op.create_index("idx_alert_rules_org", "alert_rules", ["organization_id", "is_enabled"])` |

**Query:** `SELECT * FROM alert_rules WHERE organization_id = $1 AND is_enabled = true`

The alert matcher loads all enabled rules for an organization at match time. With ~50 rules per org (5 rules × 10 orgs at MVP), this is a small table. The index is preventive — without it, every alert match would scan all rules.

**Expected improvement:** Full scan (50 rows) → filtered index scan. Marginal at MVP scale but critical at 1K+ rules per org (V1.1).

---

### Index 4: `idx_feedbacks_org_opp`

| Property | Value |
|----------|-------|
| Table | `feedbacks` |
| Columns | (organization_id, opportunity_id) |
| Type | B-tree (composite) |
| Alembic | `op.create_index("idx_feedbacks_org_opp", "feedbacks", ["organization_id", "opportunity_id"])` |

**Query:** `SELECT * FROM feedbacks WHERE organization_id = $1 AND opportunity_id = $2`

The activity feed loads all decisions for an organization's opportunities. With ~100 decisions/day per org, this grows ~3K/month. Without the index, the activity feed scans the full feedbacks table.

**Expected improvement:** Sequential scan → index scan. At 10K feedbacks: ~30ms → ~0.5ms.

---

### Index 5: `idx_opportunities_published`

| Property | Value |
|----------|-------|
| Table | `opportunities` |
| Columns | (state, published_at DESC) **WHERE state = 'published'** |
| Type | Partial B-tree |
| Alembic | `op.create_index("idx_opportunities_published", "opportunities", ["state", sa.text("published_at DESC")], postgresql_where=sa.text("state = 'published'"))` |

**Query:** `SELECT * FROM opportunities WHERE state = 'published' ORDER BY published_at DESC LIMIT 50`

Partial index — only indexes rows where `state = 'published'`. Since opportunities that are dismissed/contacted/purchased/expired never appear in the feed, indexing them is wasted I/O. The partial index is smaller (only ~25% of opportunity rows are published at any time), faster to scan, and cheaper to maintain on INSERT.

**Expected improvement:** Full scan → partial index-only scan. Index is ~75% smaller than a full index on all state values.

---

### Index 6: `idx_normalized_listings_ref`

| Property | Value |
|----------|-------|
| Table | `normalized_listings` |
| Columns | (reference_id, status, created_at DESC) |
| Type | B-tree (composite, descending) |
| Alembic | `op.create_index("idx_normalized_listings_ref", "normalized_listings", ["reference_id", "status", sa.text("created_at DESC")])` |

**Query:** `SELECT * FROM normalized_listings WHERE reference_id = $1 AND status IN ('active', 'stale') ORDER BY created_at DESC`

The reference detail page shows all listings for a specific watch reference. The composite index covers filtering (reference_id, status) and sorting (created_at DESC). At MVP with 25 references and ~200 listings per reference per month, this grows to ~5K rows per reference after 6 months.

**Expected improvement:** Sequential scan → filtered index scan. At 5K listings: ~20ms → ~1ms.

---

### Index 7: `idx_normalized_listings_active`

| Property | Value |
|----------|-------|
| Table | `normalized_listings` |
| Columns | (status, reference_id) **WHERE status = 'active'** |
| Type | Partial B-tree |
| Alembic | `op.create_index("idx_normalized_listings_active", "normalized_listings", ["status", "reference_id"], postgresql_where=sa.text("status = 'active'"))` |

**Query:** `SELECT * FROM normalized_listings WHERE status = 'active' AND reference_id = $1`

The alert matcher scans active listings by reference to find matches. Since most listings are not active (they're quarantined, suppressed, or stale), the partial index only covers the active subset — dramatically smaller than a full index.

**Expected improvement:** Full table scan → partial index scan. At 50K normalized_listings with 5K active: index is 90% smaller.

---

### Index 8: `idx_alert_deliveries_org_user`

| Property | Value |
|----------|-------|
| Table | `alert_deliveries` |
| Columns | (organization_id, user_id, created_at DESC) |
| Type | B-tree (composite, descending) |
| Alembic | `op.create_index("idx_alert_deliveries_org_user", "alert_deliveries", ["organization_id", "user_id", sa.text("created_at DESC")])` |

**Query:** `SELECT * FROM alert_deliveries WHERE organization_id = $1 AND user_id = $2 ORDER BY created_at DESC LIMIT 20`

The "My Notifications" panel shows recent deliveries for a specific user. From ADR-0002 — the index was added when `organization_id` was added to alert_deliveries for direct tenant scoping.

**Expected improvement:** Sequential scan → index scan. At 5K deliveries: ~15ms → ~1ms.

---

### Index 9: `idx_alert_deliveries_opp`

| Property | Value |
|----------|-------|
| Table | `alert_deliveries` |
| Columns | (opportunity_id, material_version) |
| Type | B-tree (composite) |
| Alembic | `op.create_index("idx_alert_deliveries_opp", "alert_deliveries", ["opportunity_id", "material_version"])` |

**Query:** `SELECT * FROM alert_deliveries WHERE opportunity_id = $1 AND material_version = $2`

The alert matcher checks whether an opportunity+version combination has already been delivered before sending a notification. This query runs for every opportunity-material_version pair during alert matching. From ADR-0002 D3 — the index was added alongside the `material_version` column.

**Expected improvement:** Sequential scan → index lookup. At 10K deliveries: ~25ms → ~0.2ms.

---

### Index 10: `idx_outbox_pending`

| Property | Value |
|----------|-------|
| Table | `outbox_events` |
| Columns | (status, created_at) **WHERE status = 'pending'** |
| Type | Partial B-tree |
| Alembic | `op.create_index("idx_outbox_pending", "outbox_events", ["status", "created_at"], postgresql_where=sa.text("status = 'pending'"))` |

**Query:** `SELECT * FROM outbox_events WHERE status = 'pending' ORDER BY created_at LIMIT 100`

The outbox worker polls for pending events, ordered by creation time. Partial index because pending events are a small fraction of all outbox events (most are `published`). Without the partial index, the worker would scan all published events too.

**Expected improvement:** Full scan → partial index scan. At 10K total events with 50 pending: 200x smaller index.

---

### Index 11: `idx_audit_org_time`

| Property | Value |
|----------|-------|
| Table | `audit_events` |
| Columns | (organization_id, created_at DESC) |
| Type | B-tree (descending) |
| Alembic | `op.create_index("idx_audit_org_time", "audit_events", ["organization_id", sa.text("created_at DESC")])` |

**Query:** `SELECT * FROM audit_events WHERE organization_id = $1 ORDER BY created_at DESC LIMIT 50`

Admin audit log browse: "Show the 50 most recent audit events for org Z." The descending index enables reverse-chronological traversal without a sort.

**Expected improvement:** Sequential scan + sort → index scan. At 10K events: ~40ms → ~2ms.

---

### Index 12: `idx_audit_resource`

| Property | Value |
|----------|-------|
| Table | `audit_events` |
| Columns | (resource_type, resource_id) |
| Type | B-tree (composite) |
| Alembic | `op.create_index("idx_audit_resource", "audit_events", ["resource_type", "resource_id"])` |

**Query:** `SELECT * FROM audit_events WHERE resource_type = 'membership' AND resource_id = $1 ORDER BY created_at DESC`

Audit drill-down: "Show all changes to membership mem_X." The composite index covers the most common audit query pattern — "what happened to this specific resource?"

**Expected improvement:** Sequential scan → index scan. At 10K events: ~30ms → ~1ms.

---

## 4. Upgrade Strategy

All 12 indexes created in a single Alembic `upgrade()` function. Order within upgrade is irrelevant (indexes are independent of each other). Convention: create in the order listed in §2.1.

```python
def upgrade() -> None:
    op.create_index("idx_memberships_org_user", "memberships", ["organization_id", "user_id"])
    op.create_index("idx_opportunities_org_state", "opportunities", 
        ["organization_id", "state", sa.text("published_at DESC")])
    op.create_index("idx_alert_rules_org", "alert_rules", ["organization_id", "is_enabled"])
    op.create_index("idx_feedbacks_org_opp", "feedbacks", ["organization_id", "opportunity_id"])
    op.create_index("idx_opportunities_published", "opportunities",
        ["state", sa.text("published_at DESC")],
        postgresql_where=sa.text("state = 'published'"))
    op.create_index("idx_normalized_listings_ref", "normalized_listings",
        ["reference_id", "status", sa.text("created_at DESC")])
    op.create_index("idx_normalized_listings_active", "normalized_listings",
        ["status", "reference_id"],
        postgresql_where=sa.text("status = 'active'"))
    op.create_index("idx_alert_deliveries_org_user", "alert_deliveries",
        ["organization_id", "user_id", sa.text("created_at DESC")])
    op.create_index("idx_alert_deliveries_opp", "alert_deliveries",
        ["opportunity_id", "material_version"])
    op.create_index("idx_outbox_pending", "outbox_events",
        ["status", "created_at"],
        postgresql_where=sa.text("status = 'pending'"))
    op.create_index("idx_audit_org_time", "audit_events",
        ["organization_id", sa.text("created_at DESC")])
    op.create_index("idx_audit_resource", "audit_events", ["resource_type", "resource_id"])
```

---

## 5. Downgrade Strategy

All 12 indexes dropped in a single `downgrade()` function. Order is irrelevant for drops, but convention follows reverse creation order.

```python
def downgrade() -> None:
    op.drop_index("idx_audit_resource", table_name="audit_events")
    op.drop_index("idx_audit_org_time", table_name="audit_events")
    op.drop_index("idx_outbox_pending", table_name="outbox_events")
    op.drop_index("idx_alert_deliveries_opp", table_name="alert_deliveries")
    op.drop_index("idx_alert_deliveries_org_user", table_name="alert_deliveries")
    op.drop_index("idx_normalized_listings_active", table_name="normalized_listings")
    op.drop_index("idx_normalized_listings_ref", table_name="normalized_listings")
    op.drop_index("idx_opportunities_published", table_name="opportunities")
    op.drop_index("idx_feedbacks_org_opp", table_name="feedbacks")
    op.drop_index("idx_alert_rules_org", table_name="alert_rules")
    op.drop_index("idx_opportunities_org_state", table_name="opportunities")
    op.drop_index("idx_memberships_org_user", table_name="memberships")
```

**Safety:** Downgrade only removes indexes. Tables remain intact. ENUMs remain intact. Foreign keys remain intact. A downgrade of 004 followed by re-upgrade of 004 is perfectly safe — no data loss.

---

## 6. Verification Queries

### Pre-upgrade

```bash
# Count indexes before 004
psql -d chronoarb -c "\di" | wc -l
# Expected: PK indexes + UNIQUE indexes only (created by DDL in 001-003)
# ~40 indexes (25 PKs + 7 UNIQUEs + 8 implicit)
```

### After upgrade

```bash
# Verify 12 new indexes exist
psql -d chronoarb -c "\di idx_*"
# Expected: 12 rows (idx_memberships_org_user through idx_audit_resource)

# Verify partial index WHERE clauses
psql -d chronoarb -c "
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE schemaname = 'public' 
  AND indexname LIKE 'idx_%'
ORDER BY indexname;
"

# Verify no redundant idempotency indexes
psql -d chronoarb -c "\di" | grep -c "idem"
# Expected: 0 (0 redundant indexes)
```

### After downgrade

```bash
# Verify indexes removed
psql -d chronoarb -c "\di idx_*"
# Expected: (0 rows)

# Verify tables intact
psql -d chronoarb -c "\dt" | wc -l
# Expected: 26 (25 tables + header)

# Verify data intact (if any was inserted before downgrade)
psql -d chronoarb -c "SELECT count(*) FROM organizations;"
# Expected: row count unchanged from before downgrade
```

### Full cycle

```bash
make db-reset                    # Clean + apply 001-004
psql -d chronoarb -c "\di idx_*" # 12 indexes
psql -d chronoarb -c "\dt" | wc -l  # 25 tables
# Downgrade 004
# psql -d chronoarb -c "\di idx_*" # 0 indexes
# psql -d chronoarb -c "\dt" | wc -l  # 25 tables (still present)
# Re-upgrade 004
# psql -d chronoarb -c "\di idx_*" # 12 indexes
```

---

## 7. Performance Checks

### Check 1: Sequential scan elimination

After creating indexes, verify that key queries use index scans instead of sequential scans:

```sql
-- Dealer feed: should use idx_opportunities_org_state or idx_opportunities_published
EXPLAIN SELECT * FROM opportunities 
WHERE organization_id = 'org_test' AND state = 'published' 
ORDER BY published_at DESC LIMIT 50;

-- Expected: Index Scan using idx_opportunities_org_state (cost ~0.5..50)
-- NOT:      Seq Scan on opportunities (cost ~0..1000)

-- Alert matching: should use idx_normalized_listings_active
EXPLAIN SELECT * FROM normalized_listings 
WHERE status = 'active' AND reference_id = 'ref_test' 
ORDER BY created_at DESC LIMIT 20;

-- Expected: Index Scan using idx_normalized_listings_active (cost ~0.5..20)
-- NOT:      Seq Scan on normalized_listings (cost ~0..500)

-- Outbox poll: should use idx_outbox_pending
EXPLAIN SELECT * FROM outbox_events 
WHERE status = 'pending' ORDER BY created_at LIMIT 100;

-- Expected: Index Scan using idx_outbox_pending (cost ~0.5..10)
-- NOT:      Seq Scan on outbox_events (cost ~0..200)
```

### Check 2: Index size estimation (empty tables)

```sql
-- Verify indexes exist and have 0 size (empty tables at MVP start)
SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) 
FROM pg_indexes 
WHERE schemaname = 'public' AND indexname LIKE 'idx_%';
-- All should show 0 bytes (no data yet)
```

### Check 3: Write overhead (minimal at MVP)

Indexes add write overhead to INSERT, UPDATE, and DELETE. At MVP scale (small tables, infrequent writes), this overhead is negligible. At production scale (100K+ rows, 100+ writes/second), the indexes will be re-evaluated with EXPLAIN ANALYZE on real data.

---

## 8. Redundant Indexes — Database-Design.md Drift

The database-design.md §3 lists 3 idempotency_key indexes that are redundant with existing UNIQUE constraints:

| Design Spec Index | Redundant With |
|-------------------|---------------|
| `idx_alert_deliveries_idem` | `uq_alert_deliveries_idempotency_key` (UNIQUE) |
| `idx_feedbacks_idem` | `uq_feedbacks_idempotency_key` (UNIQUE) |
| `idx_trade_outcomes_idem` | `uq_trade_outcomes_idempotency_key` (UNIQUE) |

PostgreSQL creates a B-tree index for every UNIQUE constraint automatically. Creating a second index on the same column is pure overhead — double the disk space, double the write I/O, zero query improvement.

**This is a deliberate deviation from database-design.md §3.** The database-design.md should be updated to reflect the corrected index list. This plan documents the decision; the implementation should verify via `\di` that no redundant `*_idem` indexes exist.

---

## 9. Index Summary

| Type | Count | Indexes |
|------|-------|---------|
| Normal (B-tree) | 9 | mems_org_user, opps_org_state, alert_rules_org, feedbacks_org_opp, norm_listings_ref, alert_deliv_org_user, alert_deliv_opp, audit_org_time, audit_resource |
| Partial (B-tree with WHERE) | 3 | opportunities_published, normalized_listings_active, outbox_pending |
| Descending | 5 | opportunities_org_state (published_at DESC), normalized_listings_ref (created_at DESC), alert_deliveries_org_user (created_at DESC), audit_org_time (created_at DESC), opportunities_published (published_at DESC) |
| Composite (multi-column) | 12 | All 12 indexes are composite (2 or more columns) |

---

## 10. ADR Compliance

| ADR | Requirement | Implementation |
|-----|-------------|---------------|
| ADR-0008 | Indexes in separate migration (004) | This migration |
| ADR-0008 | Index failures don't affect table data | No tables created, no ENUMs created |
| ADR-0008 | Independent downgrade | Drop indexes only, tables intact |
| ADR-0002 | alert_deliveries indexes (org_user, opp) | Included (indexes 8, 9) |
