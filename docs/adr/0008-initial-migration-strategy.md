# ADR-0008: Initial Migration Split Strategy

**Status:** Accepted
**Date:** 2026-08-03
**Deciders:** Lead Software Architect
**Supersedes:** None (refines WF-19 from week-01-plan.md)
**Resolves:** Migration organization for Batch 3

---

## Context

The Week 1 execution plan (week-01-plan.md §3) specifies a single `001_initial_schema.py` migration containing all 25 tables and 15+ indexes. This is the `WF-19` task, sized as Medium (90-180 minutes).

During Batch 3 planning, the following concerns were raised about a single monolithic migration:

1. **Reviewability:** A migration file with 25 table definitions, 7 ENUM types, 50+ foreign keys, and 15 indexes would span 400+ lines. Reviewing this as a single diff is error-prone.

2. **Domain boundary clarity:** The 22 tables belong to distinct domains (identity, catalog, listings, valuation, alerts, operations). Grouping them by domain makes the schema's intent clearer.

3. **Debugging granularity:** If a migration fails on table 18 of 25, the entire migration rolls back. With split migrations, only the failing domain's tables are affected, making debugging faster.

---

## Problem

A single monolithic initial migration with all 25 tables and indexes creates a reviewability and maintainability bottleneck.

---

## Decision

**The initial migration is split into 4 Alembic revisions, organized by domain boundary.**

```
alembic/versions/
├── 001_identity_and_catalog.py    (tables 1-9)
├── 002_listings_and_valuation.py  (tables 10-17)
├── 003_alerts_and_operations.py   (tables 18-25)
└── 004_indexes.py                 (15+ indexes)
```

### Revision Chain

```
None
  ↓
001_identity_and_catalog     (organizations, users, memberships, brands, references, aliases, watch_lists, watch_list_entries, sources)
  ↓
002_listings_and_valuation   (raw_snapshots, parsed_listings, normalized_listings, duplicate_groups, duplicate_group_members, valuations, opportunities, opportunity_views)
  ↓
003_alerts_and_operations    (alert_rules, alert_deliveries, feedbacks, trade_outcomes, subscriptions, audit_events, outbox_events, feature_flags)
  ↓
004_indexes                  (15+ compound indexes)
```

### Domain Grouping Rationale

| Migration | Domain | Rationale |
|-----------|--------|-----------|
| 001 | Identity + Catalog | Core reference data. Must exist before everything else. All FK targets originate here. |
| 002 | Listings + Valuation | Pipeline data. Depends on identity (organization/user FKs) and catalog (reference/brand FKs). |
| 003 | Alerts + Operations | Business process data. Depends on listings (opportunity/valuation FKs from 002). Independent of 001 structure beyond FKs. |
| 004 | Indexes | Performance layer. Must run after all tables exist. No FK dependencies — only index creation. |

### Indexes in Separate Migration

Indexes are placed in a dedicated file (004) rather than inline with table definitions because:

- Index creation does not affect the migration's logical correctness — it only affects query performance
- If an index DDL fails, tables are unaffected (no rollback of 001-003)
- Indexes can be verified independently with `\di` without scanning table definitions
- Future indexes added in expand/contract migrations will follow the same pattern (separate migration files)

---

## Alternatives Considered

### Alternative A: Single monolithic migration (rejected)

One `001_initial_schema.py` with all 22 tables and indexes.

**Rejected because:** A 400+ line migration file is hard to review, debug, and reason about. If it fails on table 18, all 22 tables roll back. The domain boundaries are implicit in the DDL ordering, not explicit in the file organization.

### Alternative B: One migration per table (rejected)

22 separate migration files, one per table.

**Rejected because:** Creates excessive migration overhead. Some tables (organizations + memberships + users) are tightly coupled and must be created together to satisfy FK constraints. Splitting to this granularity would require temporary constraint deferral or intermediate migration states that are never valid.

### Alternative C: Indexes inline with table migrations (rejected)

Add `CREATE INDEX` statements to 001/002/003 alongside the table definitions.

**Rejected because:** Index creation is a performance concern, not a schema concern. Mixing DDL (CREATE TABLE) with DML-adjacent operations (CREATE INDEX) in the same migration violates the single-responsibility principle at the migration level. A failed index should not force table rollback.

---

## Consequences

### Positive

- Each migration is <150 lines (reviewable in a single screen)
- DB-06, DB-07, DB-08 can be written in parallel by different engineers
- Migration failures are isolated to the failing domain
- Index creation is independent — a bad index DDL doesn't affect table data
- Domain grouping serves as implicit documentation of the schema's logical structure

### Negative

- 4 migration files instead of 1 (more files to navigate)
- Alembic revision chain is 4 deep instead of 1 deep (minor — Alembic handles this transparently)
- Cannot `alembic downgrade` to a state with only identity tables and partial listing tables — the chain is ordered

### Neutral

- `alembic upgrade head` and `alembic downgrade base` behave identically to a single migration
- `alembic current` shows the revision chain depth (4) instead of 1
- Future migrations append to the chain (005, 006, ...) regardless of initial split

---

## Testing Implications

### Downgrade Testing

Each migration file must have a verified `downgrade()` function. The order is:

```bash
alembic downgrade -1  # 004 → 003 (drop indexes only)
alembic downgrade -1  # 003 → 002 (drop alert/operations tables)
alembic downgrade -1  # 002 → 001 (drop listing/valuation tables)
alembic downgrade -1  # 001 → None (drop identity/catalog tables)
```

### Integration Test

```bash
alembic downgrade base    # All 4 reversed
alembic upgrade head      # All 4 re-applied
psql -d chronoarb -c "\dt" | wc -l  # 22 tables
```

---

## Migration Impact

- **Batch 3 tasks DB-06/07/08/09** implement this decision
- **No existing migrations to modify** — this is the first migration set
- **Future migrations** append to the chain (005, 006, ...) following the same domain-grouping convention when multiple related changes are made
- **Downstream impact:** None. Repository implementations (Week 3-5) interact with tables via SQLAlchemy sessions, not Alembic revisions.

---

## References

- week-01-plan.md §3: WF-19 (original single migration task)
- batch-03-database-plan.md: Tasks DB-06 through DB-09
- database-design.md §2: All 22 table definitions
- ADR-0002: alert_deliveries schema corrections
- ADR-0004: observation_at on normalized_listings
- ADR-0005: fx_source + fx_date on normalized_listings
