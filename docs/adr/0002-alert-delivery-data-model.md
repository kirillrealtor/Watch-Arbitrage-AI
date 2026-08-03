# ADR-0002: Alert Deliveries Data Model

**Status:** Accepted
**Date:** 2026-08-03
**Deciders:** Lead Software Architect
**Supersedes:** None
**Resolves:** Architecture Review BLOCKER-01, MAJOR-05

---

## Context

The database design document (`database-design.md`) defines the `alert_deliveries` table with a `UNIQUE(rule_id, user_id, opportunity_id, channel, material_version)` constraint that references a `material_version` column not present on the table. Additionally, `alert_deliveries` is tenant-scoped data but lacks an explicit `organization_id` column, relying on a JOIN through `alert_rules` for tenant scoping.

The `idempotency_key` column, defined as `SHA256(organization_id + user_id + rule_id + opportunity_id + material_version + channel)`, already encodes the full uniqueness set. It has a `UNIQUE NOT NULL` constraint.

---

## Problem

### P1: Invalid UNIQUE constraint

```sql
-- From database-design.md
alert_deliveries
├── idempotency_key    TEXT UNIQUE NOT NULL
└── UNIQUE(rule_id, user_id, opportunity_id, channel, material_version)
```

The composite UNIQUE references `material_version`, which is not defined on this table. The migration would fail.

### P2: Missing explicit tenant scope

`alert_deliveries` stores per-user, per-organization delivery records but lacks `organization_id`. The tenant scope can only be resolved via `rule_id → alert_rules.organization_id`, which:
- Requires a JOIN for every tenant-scoped query
- Creates a risk of forgetting the tenant filter
- Violates the pattern established in ADR-0001 D7 of direct tenant scoping on tenant-data tables

### P3: Redundant uniqueness enforcement

The `idempotency_key` already encodes the SHA256 hash of all uniqueness dimensions. A composite UNIQUE constraint duplicates this guarantee with no additional protection.

---

## Decision

### D1: Remove the composite UNIQUE constraint

The `idempotency_key TEXT UNIQUE NOT NULL` column is the sole uniqueness enforcement mechanism for `alert_deliveries`. The composite UNIQUE constraint is removed entirely.

**Rationale:**
- The idempotency key is generated at match time and already encodes `(organization_id, user_id, rule_id, opportunity_id, material_version, channel)`.
- Database-level `UNIQUE(idempotency_key)` provides the same guarantee as a composite UNIQUE over the constituent columns.
- A composite UNIQUE containing `material_version` would require adding the column to the table, which is unnecessary when the idempotency key provides the guarantee.
- SHA256 collision probability is negligible for this use case (well under 2^-128).

### D2: Add `organization_id` to alert_deliveries

Add `organization_id FK → organizations.id NOT NULL` as a direct column on `alert_deliveries`.

**Rationale:**
- Consistent with ADR-0001 D7: "Every repository method that accesses tenant data shall require an explicit organization_id parameter."
- Eliminates the need to JOIN through `alert_rules` for tenant-scoped queries.
- The value is known at insert time (derived from `alert_rules.organization_id` at match time).

### D3: Add `material_version` column for query performance

Add `material_version INT NOT NULL` to `alert_deliveries`, populated at insert time from the opportunity's current material version.

**Rationale:**
- Enables efficient queries like "show deliveries for opportunity v3" without joining to opportunities.
- Supports delivery history view where the user wants to see which version triggered which notification.
- The value is known at match time and costs nothing to store.
- Not used for uniqueness enforcement.

### Corrected schema:

```sql
alert_deliveries
├── id (PK)              ULID
├── organization_id       FK → organizations.id NOT NULL
├── rule_id               FK → alert_rules.id NOT NULL
├── user_id               FK → users.id NOT NULL
├── opportunity_id        FK → opportunities.id NOT NULL
├── material_version      INT NOT NULL
├── channel               TEXT NOT NULL       (telegram, push)
├── idempotency_key       TEXT UNIQUE NOT NULL
├── delivery_status       ENUM(pending, sent, failed, suppressed)
├── provider_message_id   TEXT
├── created_at            TIMESTAMPTZ
```

Indexes (added to database-design.md §3):

```sql
CREATE INDEX idx_alert_deliveries_idem ON alert_deliveries(idempotency_key);
CREATE INDEX idx_alert_deliveries_org_user ON alert_deliveries(organization_id, user_id, created_at DESC);
CREATE INDEX idx_alert_deliveries_opp ON alert_deliveries(opportunity_id, material_version);
```

---

## Alternatives Considered

### Alternative A: Add material_version column and keep composite UNIQUE

Add the missing column plus a partial unique index:

```sql
ALTER TABLE alert_deliveries ADD COLUMN material_version INT NOT NULL;
CREATE UNIQUE INDEX idx_alert_deliveries_unique
  ON alert_deliveries(rule_id, user_id, opportunity_id, channel, material_version);
```

**Rejected because:** The idempotency_key already provides the guarantee. Maintaining two uniqueness mechanisms for the same logical constraint adds schema complexity and a second index for no benefit. The composite index would still be useful for queries, but not as a UNIQUE constraint.

### Alternative B: No material_version column, idempotency_key only

Use only `idempotency_key UNIQUE` without adding `material_version` as a column. The version is encoded in the key but not queryable.

**Rejected because:** Querying by `material_version` is a supported use case (delivery history, re-alert logic). Storing it as a column costs nothing and enables efficient queries.

### Alternative C: No organization_id, JOIN through rule_id

Rely on `rule_id → alert_rules.organization_id` for tenant scoping.

**Rejected because:** Violates ADR-0001 D7 tenant isolation pattern. Requires JOIN for every tenant-scoped delivery query. Increases risk of missing tenant filter.

---

## Consequences

### Positive

- Schema is migratable (no undefined-column constraint).
- Single, clear uniqueness mechanism (idempotency key).
- Direct tenant scoping consistent with the rest of the data model.
- `material_version` enables efficient delivery history queries.
- No duplication of uniqueness enforcement.

### Negative

- Two new columns (`organization_id`, `material_version`) add to the migration.
- `organization_id` is denormalized (exists on both `alert_rules` and `alert_deliveries`). This is accepted as a deliberate denormalization for tenant isolation consistency.

### Neutral

- The idempotency key generation formula (`SHA256(org + user + rule + opp + material_version + channel)`) is now the sole source of delivery uniqueness. Its correctness must be verified in contract tests.

---

## Migration Impact

### New migration (Week 1-2, alongside initial schema creation):

```sql
-- This replaces the original alert_deliveries definition in the initial migration.
-- No expand/contract needed since this is a brand-new table.

CREATE TABLE alert_deliveries (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    rule_id TEXT NOT NULL REFERENCES alert_rules(id),
    user_id TEXT NOT NULL REFERENCES users(id),
    opportunity_id TEXT NOT NULL REFERENCES opportunities(id),
    material_version INTEGER NOT NULL,
    channel TEXT NOT NULL,
    idempotency_key TEXT UNIQUE NOT NULL,
    delivery_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (delivery_status IN ('pending', 'sent', 'failed', 'suppressed')),
    provider_message_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alert_deliveries_idem ON alert_deliveries(idempotency_key);
CREATE INDEX idx_alert_deliveries_org_user ON alert_deliveries(organization_id, user_id, created_at DESC);
CREATE INDEX idx_alert_deliveries_opp ON alert_deliveries(opportunity_id, material_version);
```

No backfill needed (greenfield table). No expand/contract needed.

---

## Testing Implications

### Contract tests
- Verify that `idempotency_key` generation is deterministic: same inputs → same key.
- Verify that different `material_version` values produce different keys for the same opportunity.
- Verify that different `organization_id` values produce different keys for the same rule+user+opportunity combo.

### Integration tests
- Insert with duplicate `idempotency_key` → UNIQUE constraint violation (expected).
- Verify alert matcher worker populates `organization_id` from `alert_rules.organization_id`.
- Verify alert matcher worker populates `material_version` from `opportunities.material_version`.
- Cross-tenant access test: user in org A cannot see deliveries for org B.

### Domain tests
- `generate_idempotency_key(org_id, user_id, rule_id, opp_id, material_version, channel)` produces stable output.
- Sorting of components in the hash input is deterministic (alphabetical by component type, not insertion order).

---

## References

- ADR-0001 D6: Idempotency by Design
- ADR-0001 D7: Tenant Isolation via Mandatory organization_id
- Architecture Review: BLOCKER-01, MAJOR-05
- database-design.md §2.8 (original alert_deliveries definition)
- worker-design.md §3.5 (Alert Matcher Worker)
- worker-design.md §4 (Idempotency Rules)
