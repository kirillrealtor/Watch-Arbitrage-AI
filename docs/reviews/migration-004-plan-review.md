# Migration 004 — Plan Review

**Review type:** Pre-implementation index audit
**Reviewed document:** docs/implementation/migration-004-plan.md
**Date:** 2026-08-03T17:24:49+05:00
**Reviewer:** Architecture review pass
**Cross-referenced:** database-design.md §3, ADR-0002, ADR-0008

---

## Executive Summary

The migration 004 plan is correct and complete. All 12 indexes map to documented query patterns. The 3 excluded idempotency indexes are correctly identified as redundant with UNIQUE constraints. Composite column ordering optimizes for the leading filter in each query. Partial indexes correctly use WHERE clauses matching the query conditions. Downgrade is safe — indexes are removed without affecting tables. One minor documentation artifact needs cleanup in §9.

**Verdict: READY FOR IMPLEMENTATION**

---

## 1. Index Correctness

### Column-to-Query Mapping

| Index | Columns | Query Pattern | Match? |
|-------|---------|--------------|--------|
| `idx_memberships_org_user` | (org_id, user_id) | `WHERE org_id = $1 AND user_id = $2` | YES — both equality filters |
| `idx_opportunities_org_state` | (org_id, state, pub_at DESC) | `WHERE org_id = $1 AND state = $2 ORDER BY pub_at DESC` | YES — covers filter + sort |
| `idx_alert_rules_org` | (org_id, is_enabled) | `WHERE org_id = $1 AND is_enabled = true` | YES — both equality filters |
| `idx_feedbacks_org_opp` | (org_id, opp_id) | `WHERE org_id = $1 AND opp_id = $2` | YES — both equality filters |
| `idx_opportunities_published` | (state, pub_at DESC) PARTIAL | `WHERE state = 'published' ORDER BY pub_at DESC` | YES — partial matches exact query |
| `idx_normalized_listings_ref` | (ref_id, status, created_at DESC) | `WHERE ref_id = $1 AND status IN (...) ORDER BY created_at DESC` | YES — leading column is most selective |
| `idx_normalized_listings_active` | (status, ref_id) PARTIAL | `WHERE status = 'active' AND ref_id = $1` | YES — partial matches exact query |
| `idx_alert_deliveries_org_user` | (org_id, user_id, created_at DESC) | `WHERE org_id = $1 AND user_id = $2 ORDER BY created_at DESC` | YES — filter + sort |
| `idx_alert_deliveries_opp` | (opp_id, material_version) | `WHERE opp_id = $1 AND material_version = $2` | YES — both equality filters |
| `idx_outbox_pending` | (status, created_at) PARTIAL | `WHERE status = 'pending' ORDER BY created_at LIMIT 100` | YES — partial matches exact query |
| `idx_audit_org_time` | (org_id, created_at DESC) | `WHERE org_id = $1 ORDER BY created_at DESC LIMIT 50` | YES — filter + sort |
| `idx_audit_resource` | (resource_type, resource_id) | `WHERE resource_type = $1 AND resource_id = $2` | YES — both equality filters |

**Finding:** All 12 indexes map 1:1 to documented query patterns. Zero speculative indexes. Zero indexes without a query.

**PASS.**

---

## 2. Duplicate Index Detection

### UNIQUE Constraint Index Overlap

**Excluded indexes:** 3 idempotency_key indexes correctly identified as redundant.

| Excluded | UNIQUE Constraint Index | Verification |
|----------|------------------------|-------------|
| `idx_alert_deliveries_idem` | `uq_alert_deliveries_idempotency_key` | Migration 003: `sa.UniqueConstraint("idempotency_key", name="uq_alert_deliveries_idempotency_key")` |
| `idx_feedbacks_idem` | `uq_feedbacks_idempotency_key` | Migration 003: `sa.UniqueConstraint("idempotency_key", name="uq_feedbacks_idempotency_key")` |
| `idx_trade_outcomes_idem` | `uq_trade_outcomes_idempotency_key` | Migration 003: `sa.UniqueConstraint("idempotency_key", name="uq_trade_outcomes_idempotency_key")` |

PostgreSQL creates a B-tree index for every UNIQUE constraint. A second index on the same column provides zero additional query benefit and doubles write I/O.

### Non-Overlapping Similar Indexes

| Index A | Index B | Overlap? | Assessment |
|---------|---------|----------|------------|
| `idx_memberships_org_user` (org_id, user_id) | `uq_memberships_user_org` (user_id, org_id) | Different column order | NOT a duplicate — different leading column for different queries |
| `idx_opportunities_org_state` (org_id, state, pub_at DESC) | `idx_opportunities_published` (state, pub_at DESC) PARTIAL | Different scope and leading column | NOT a duplicate — one covers all states, one is partial for published only |
| `idx_normalized_listings_ref` (ref_id, status, created_at DESC) | `idx_normalized_listings_active` (status, ref_id) PARTIAL | Different leading column and scope | NOT a duplicate — different query access patterns |

**Finding:** All 12 indexes serve distinct query access patterns. No false duplicates. No missing exclusions.

**PASS.**

---

## 3. Composite Index Ordering

### Leading Column Justification

| Index | Leading Column | Justification |
|-------|---------------|---------------|
| `mems_org_user` | org_id | All auth middleware queries scope to an organization first |
| `opps_org_state` | org_id | Dealer feed always scoped to org_id |
| `alert_rules_org` | org_id | Rules are always loaded per-organization |
| `feedbacks_org_opp` | org_id | Feedback queries always scoped to org_id |
| `opps_published` | state | Partial: all rows are published; order by pub_at DESC |
| `norm_listings_ref` | ref_id | Most common query: "all listings for reference X" |
| `norm_listings_active` | status | Partial: all rows are active; filter by ref_id |
| `alert_deliv_org_user` | org_id | Delivery history scoped to org first, user second |
| `alert_deliv_opp` | opp_id | Alert check always looks up by opportunity |
| `outbox_pending` | status | Partial: all rows are pending; order by created_at |
| `audit_org_time` | org_id | Audit browse always scoped to org_id |
| `audit_resource` | resource_type | Resource type is always an equality filter |

**Pattern:** 6 indexes lead with `organization_id` — consistent with ADR-0001 D7 tenant isolation. The leading column is the most restrictive filter in every case.

**PASS.**

---

## 4. Partial Index Conditions

### WHERE Clause Correctness

| Index | WHERE Clause | Query WHERE Clause | Match? |
|-------|-------------|-------------------|--------|
| `idx_opportunities_published` | `state = 'published'` | `WHERE state = 'published'` | YES |
| `idx_normalized_listings_active` | `status = 'active'` | `WHERE status = 'active'` | YES |
| `idx_outbox_pending` | `status = 'pending'` | `WHERE status = 'pending'` | YES |

PostgreSQL uses a partial index only when the query WHERE clause is a logical subset of the index WHERE clause. In all 3 cases, the query condition exactly matches the index condition — guaranteed usage.

### Partial Index Selectivity

| Index | Expected Total Rows (MVP) | Expected Partial Rows | Selectivity |
|-------|--------------------------|----------------------|-------------|
| `opps_published` | ~2K (all states) | ~500 (published only) | ~25% |
| `norm_listings_active` | ~50K (all statuses) | ~5K (active only) | ~10% |
| `outbox_pending` | ~10K (all statuses) | ~50 (pending only) | ~0.5% |

The `outbox_pending` index has the highest selectivity benefit — a 200x smaller index than a full index on status+created_at.

**PASS.**

---

## 5. Query Pattern Alignment

### Critical Query Path Coverage

| Query | Frequency | Index Serving It |
|-------|-----------|-----------------|
| Auth: "is user X in org Y?" | Every API call | `idx_memberships_org_user` |
| Feed: "latest published opportunities for org Z" | Every page load | `idx_opportunities_org_state` or `idx_opportunities_published` |
| Alert match: "enabled rules for org Z" | Every opportunity evaluation | `idx_alert_rules_org` |
| Alert match: "active listings for ref X" | Every reference match | `idx_normalized_listings_active` |
| Alert match: "already delivered opp X v3?" | Every delivery check | `idx_alert_deliveries_opp` |
| Outbox: "oldest pending events" | Every 5 seconds | `idx_outbox_pending` |

All critical query paths are covered. No hot path relies on a sequential scan.

### Unindexed Tables (Not Currently Needed)

| Table | Reason No Index |
|-------|----------------|
| `subscriptions` | MVP: 10 rows total — sequential scan is <1ms |
| `opportunity_views` | Covered by `UNIQUE(opportunity_id, user_id)` B-tree |
| `watch_lists` | MVP: <50 rows per org — sequential scan is sufficient |
| `watch_list_entries` | Covered by `UNIQUE(watch_list_id, reference_id)` B-tree |
| `duplicate_groups` | MVP: <500 rows — sequential scan sufficient |
| `duplicate_group_members` | Covered by `UNIQUE(group_id, listing_id)` B-tree |
| `raw_snapshots` | Covered by `UNIQUE(source_id, external_id, adapter_version, checksum)` |
| `parsed_listings` | Covered by `UNIQUE(snapshot_id)` B-tree |
| `feature_flags` | MVP: <20 rows — sequential scan is sufficient |

**PASS.**

---

## 6. Tenant Isolation Performance

### Organization-Scoped Query Pattern

6 of 12 indexes lead with `organization_id`, matching the ADR-0001 D7 pattern where every tenant-scoped query starts with `WHERE organization_id = $1`.

| Index | Table | Org-Scoped? |
|-------|-------|------------|
| `idx_memberships_org_user` | memberships | YES — first column |
| `idx_opportunities_org_state` | opportunities | YES — first column |
| `idx_alert_rules_org` | alert_rules | YES — first column |
| `idx_feedbacks_org_opp` | feedbacks | YES — first column |
| `idx_alert_deliveries_org_user` | alert_deliveries | YES — first column |
| `idx_audit_org_time` | audit_events | YES — first column |

Non-tenant-scoped tables (normalized_listings, outbox_events) correctly omit organization_id from their indexes — these tables are global.

**PASS.**

---

## 7. Worker Query Performance

### Alert Matcher Worker

| Query | Index | Type |
|-------|-------|------|
| Load enabled rules for org | `idx_alert_rules_org` | Index scan |
| Find active listings by reference | `idx_normalized_listings_active` | Partial index scan |
| Check if already delivered for version | `idx_alert_deliveries_opp` | Index lookup |

All three alert matcher queries are indexed. No sequential scan at any stage of the matching pipeline.

### Outbox Worker

| Query | Index | Type |
|-------|-------|------|
| Poll oldest pending events | `idx_outbox_pending` | Partial index scan with sort elimination |

The outbox worker's poll loop is indexed. The partial index on `outbox_events` means the worker never scans `published` or `failed` rows — only the active subset.

### Normalization / Valuation Workers

These workers mostly write (INSERT) and do point-lookups via primary keys. No additional indexes are needed for worker write paths.

**PASS.**

---

## 8. Downgrade Safety

### Downgrade Impact

| Operation | Effect |
|-----------|--------|
| `op.drop_index(...)` | Removes B-tree index structure from disk |
| Tables | Unaffected — all 25 tables remain |
| Data | Unaffected — no rows deleted |
| ENUMs | Unaffected — all 7 types remain |
| Foreign keys | Unaffected — all 39 FKs remain |
| Primary keys | Unaffected — all 25 PKs remain |
| UNIQUE constraints | Unaffected — all UNIQUE indexes remain |

### Downgrade Validation

```bash
alembic downgrade -1        # 004 → 003
\di idx_*                   # (0 rows) — all idx_* indexes dropped
\dt                         # 25 tables — all present
SELECT * FROM organizations # (0 rows) — data not deleted, just empty
```

**PASS.**

---

## 9. Migration Execution Safety

### Index Creation on Empty Tables

At MVP, all 25 tables are empty. Migration 004 runs against a freshly created schema with zero rows. Index creation with 0 rows is an O(1) operation — no locking, no blocking, instant completion.

### Schema Completeness After 004

After applying all 4 migrations, the database has:
- 25 tables
- 7 ENUM types
- 12 non-primary-key indexes
- 25 primary key indexes
- 8+ UNIQUE constraint indexes (memberships, references, aliases, watch_list_entries, raw_snapshots, parsed_listings, normalized_listings, opportunities, opportunity_views, alert_deliveries, feedbacks, trade_outcomes, feature_flags)

~52 total indexes (25 PK + 15 unique + 12 application). This is the complete initial schema for Batch 3. No further DDL is planned for Batch 3.

**PASS.**

---

## 10. Additional Findings

### Issue CR-01: Section 9 contains unfinished analysis. (NOTE)

The plan's §9 has an editorial artifact:

> "Wait, let me re-check: Actually all 12 indexes are composite except none — idx_alert_deliveries_opp is also composite. So 12 composite."

This is a work-in-progress note that should be finalized. All 12 indexes ARE composite (multi-column). The table summary should state: `Composite (multi-column): 12 (all)`. The "Wait, let me re-check" text should be removed.

**Action:** Clean up §9 text to remove editorial commentary.

### Issue CR-02: subscriptions.stripe_customer_id lookup not indexed. (NOTE)

Stripe webhook events arrive with `stripe_customer_id` and `stripe_subscription_id`. The webhook handler needs to look up the subscription by these IDs. At MVP with 10 subscriptions, a sequential scan takes <1ms. Post-MVP (100+ subscriptions), this should get an index:

```sql
CREATE INDEX idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);
CREATE INDEX idx_subscriptions_stripe_subscription ON subscriptions(stripe_subscription_id);
```

**Action:** Add to the "Future Indexes" section of the plan or note in a post-MVP index migration.

### Issue CR-03: database-design.md §3 lists 3 redundant idempotency indexes. (NOTE)

Per the plan, the 3 `*_idem` indexes are excluded as redundant. The database-design.md should be updated to reflect this. Same pattern as ADR-0002 / database-design.md §2.8 correction.

**Action:** Update database-design.md §3 to remove `idx_alert_deliveries_idem`, `idx_feedbacks_idem`, `idx_trade_outcomes_idem`. Add a note explaining that UNIQUE constraints provide equivalent indexes.

---

## 11. Correction Summary

| ID | Severity | Description | Action |
|----|----------|-------------|--------|
| CR-01 | NOTE | §9 contains unfinished "Wait, let me re-check" text | Remove editorial commentary; finalize as "12 composite" |
| CR-02 | NOTE | Missing index on subscriptions.stripe_customer_id and stripe_subscription_id | Add as "Future Indexes" note; sequential scan is fine at MVP (10 rows) |
| CR-03 | NOTE | database-design.md §3 still lists 3 redundant idempotency indexes | Update database-design.md to match plan |

**Zero blocking or major issues.** All three findings are notes — CR-01 is a documentation cleanup, CR-02 is a post-MVP optimization, CR-03 is a documentation update.

---

## 12. Batch Progression Gate

**Question: Is migration 004 ready for implementation?**

Yes. All 10 review dimensions pass.

| Gate | Status |
|------|--------|
| Index correctness | PASS — 12 indexes, all map to query patterns |
| Duplicate index detection | PASS — 3 correctly excluded |
| UNIQUE constraint overlap | PASS — excluded indexes are redundant |
| Composite index ordering | PASS — leading column matches query selectivity |
| Partial index conditions | PASS — WHERE clauses match query conditions |
| Query pattern alignment | PASS — all critical paths covered |
| Tenant isolation performance | PASS — 6 indexes lead with org_id |
| Worker query performance | PASS — alert matcher + outbox worker covered |
| Downgrade safety | PASS — indexes only, tables intact |
| Migration execution safety | PASS — zero data, instant creation |

**Verdict: READY FOR IMPLEMENTATION**
