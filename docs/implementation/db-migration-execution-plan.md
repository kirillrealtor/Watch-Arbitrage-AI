# ChronoArb — DB Migration Execution Plan

**Plan type:** Migration authoring guide
**Batch:** 3, DB-06 through DB-09
**Date:** 2026-08-03T15:51:10+05:00
**Status:** Ready for implementation
**References:** ADR-0008 (split strategy), database-design.md §2-3, ADR-0002/0004/0005

---

## 1. Migration Order

```
Alembic revision chain (linear, no branches):

None
  ↓
001_identity_and_catalog     (tables  1–9,  ENUMs: membership_role)
  ↓
002_listings_and_valuation   (tables 10–17, ENUMs: listing_status, opportunity_state)
  ↓
003_alerts_and_operations    (tables 18–25, ENUMs: delivery_status, feedback_decision, subscription_status, outbox_event_status)
  ↓
004_indexes                  (15+ indexes across all 25 tables)
```

---

## 2. Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│ 001_identity_and_catalog                                        │
│                                                                 │
│ ENUM: membership_role                                           │
│                                                                 │
│ organizations ──────────────────────────────────────────────┐   │
│ users                                                       │   │
│ memberships ─── FK → organizations, users, users(inviter)    │   │
│ brands                                                       │   │
│ references ───── FK → brands                                 │   │
│ aliases ──────── FK → references                             │   │
│ watch_lists ──── FK → organizations                          │   │
│ watch_list_entries → FK → watch_lists, FK → references       │   │
│ sources                                                      │   │
└──────────────────────────────────────────────────────────────┘   │
                                    │                              │
                                    ▼                              │
┌──────────────────────────────────────────────────────────────────┐
│ 002_listings_and_valuation                                       │
│                                                                  │
│ ENUM: listing_status, opportunity_state                          │
│                                                                  │
│ raw_snapshots ────────── FK → sources (001)                      │
│ parsed_listings ──────── FK → raw_snapshots ◄────────────────────┘
│ normalized_listings ──── FK → parsed_listings, FK → references (001)
│ duplicate_groups ─────── FK → normalized_listings (representative)
│ duplicate_group_members ─ FK → duplicate_groups, FK → normalized_listings
│ valuations ───────────── FK → normalized_listings
│ opportunities ────────── FK → organizations (001), FK → normalized_listings, FK → valuations
│ opportunity_views ────── FK → opportunities, FK → users (001)
└──────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│ 003_alerts_and_operations                                        │
│                                                                  │
│ ENUM: delivery_status, feedback_decision,                        │
│       subscription_status, outbox_event_status                   │
│                                                                  │
│ alert_rules ──────────── FK → organizations (001), FK → users (001)
│ alert_deliveries ─────── FK → organizations (001), FK → alert_rules,
│                          FK → users (001), FK → opportunities (002)
│ feedbacks ────────────── FK → organizations (001), FK → users (001),
│                          FK → opportunities (002)
│ trade_outcomes ───────── FK → organizations (001), FK → users (001),
│                          FK → opportunities (002, nullable),
│                          FK → references (001)
│ subscriptions ────────── FK → organizations (001)
│ audit_events ─────────── FK → organizations (001, nullable),
│                          FK → users (001, nullable)
│ outbox_events ────────── (no FKs)
│ feature_flags ────────── (no FKs)
└──────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│ 004_indexes                                                     │
│                                                                  │
│ 15+ compound indexes across all 25 tables                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Foreign Key Ordering (Per Migration)

### 001_identity_and_catalog

Tables must be created in this order (children after parents):

```
1. organizations         ← no FKs
2. users                  ← no FKs
3. brands                 ← no FKs
4. watch_lists            ← FK → organizations
5. references             ← FK → brands
6. sources                ← no FKs
7. memberships            ← FK → organizations, FK → users, FK → users
8. aliases                ← FK → references
9. watch_list_entries     ← FK → watch_lists, FK → references
```

**Downgrade:** Reverse order (9 → 1).

### 002_listings_and_valuation

```
10. raw_snapshots              ← FK → sources (001)
11. parsed_listings            ← FK → raw_snapshots
12. normalized_listings        ← FK → parsed_listings, FK → references (001)
13. duplicate_groups           ← FK → normalized_listings
14. duplicate_group_members    ← FK → duplicate_groups, FK → normalized_listings
15. valuations                 ← FK → normalized_listings
16. opportunities              ← FK → organizations (001), FK → normalized_listings, FK → valuations
17. opportunity_views          ← FK → opportunities, FK → users (001)
```

**Downgrade:** Reverse order (17 → 10).

### 003_alerts_and_operations

```
18. alert_rules            ← FK → organizations (001), FK → users (001)
19. alert_deliveries       ← FK → organizations (001), FK → alert_rules,
                              FK → users (001), FK → opportunities (002)
20. feedbacks              ← FK → organizations (001), FK → users (001),
                              FK → opportunities (002)
21. trade_outcomes         ← FK → organizations (001), FK → users (001),
                              FK → opportunities (002, nullable),
                              FK → references (001)
22. subscriptions          ← FK → organizations (001)
23. audit_events           ← FK → organizations (001, nullable),
                              FK → users (001, nullable)
24. outbox_events          ← (no FKs)
25. feature_flags          ← (no FKs)
```

**Downgrade:** Reverse order (25 → 18).

---

## 4. Migration Specifications

### 001_identity_and_catalog

- **Revision ID:** Auto-generated by Alembic
- **Down revision:** None (first in chain)
- **Tables:** 9
- **ENUMs created:** `membership_role`

| # | Table | Key Columns | Constraints |
|---|-------|-------------|-------------|
| 1 | `organizations` | id (TEXT PK), name (TEXT NOT NULL), slug (TEXT UNIQUE NOT NULL), settings (JSONB), created_at (TIMESTAMPTZ DEFAULT NOW()), updated_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, UNIQUE: slug |
| 2 | `users` | id (TEXT PK), cognito_sub (TEXT UNIQUE NOT NULL), email (TEXT UNIQUE NOT NULL), display_name (TEXT), created_at (TIMESTAMPTZ DEFAULT NOW()), updated_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, UNIQUE: cognito_sub, email |
| 3 | `brands` | id (TEXT PK), name (TEXT UNIQUE NOT NULL), slug (TEXT UNIQUE NOT NULL), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, UNIQUE: name, slug |
| 4 | `watch_lists` | id (TEXT PK), organization_id (FK → organizations NOT NULL), name (TEXT NOT NULL), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: organization_id |
| 5 | `references` | id (TEXT PK), brand_id (FK → brands NOT NULL), ref_code (TEXT NOT NULL), model_name (TEXT), generation (TEXT), attributes (JSONB), is_active (BOOLEAN DEFAULT true), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: brand_id, UNIQUE: (brand_id, ref_code) |
| 6 | `sources` | id (TEXT PK), source_key (TEXT UNIQUE NOT NULL), display_name (TEXT NOT NULL), adapter_version (TEXT NOT NULL), access_mode (TEXT NOT NULL), rate_policy (JSONB), approval_ref (TEXT), is_enabled (BOOLEAN DEFAULT false), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, UNIQUE: source_key |
| 7 | `memberships` | id (TEXT PK), organization_id (FK → organizations NOT NULL), user_id (FK → users NOT NULL), role (membership_role NOT NULL), invited_by (FK → users NULLABLE), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: org_id, user_id, invited_by, UNIQUE: (user_id, organization_id) |
| 8 | `aliases` | id (TEXT PK), reference_id (FK → references NOT NULL), alias_text (TEXT NOT NULL), source (TEXT) | PK: id, FK: reference_id, UNIQUE: (alias_text, source) |
| 9 | `watch_list_entries` | id (TEXT PK), watch_list_id (FK → watch_lists NOT NULL), reference_id (FK → references NOT NULL), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: watch_list_id, reference_id, UNIQUE: (watch_list_id, reference_id) |

**Upgrade verification:**
```bash
psql -d chronoarb -c "\dt" | wc -l  # 9 tables + header
psql -d chronoarb -c "\d organizations"
psql -d chronoarb -c "\d memberships"
psql -d chronoarb -c "SELECT typname FROM pg_type WHERE typname='membership_role';"
```

**Downgrade verification:**
```bash
alembic downgrade -1
psql -d chronoarb -c "\dt" | wc -l  # 0 tables
```

---

### 002_listings_and_valuation

- **Revision ID:** Auto-generated by Alembic
- **Down revision:** `001_identity_and_catalog`
- **Tables:** 8
- **ENUMs created:** `listing_status`, `opportunity_state`
- **ADR corrections:** ADR-0004 (observation_at), ADR-0005 (fx_source, fx_date)

| # | Table | Key Columns | Constraints |
|---|-------|-------------|-------------|
| 10 | `raw_snapshots` | id (TEXT PK), source_id (FK → sources NOT NULL), external_id (TEXT NOT NULL), adapter_version (TEXT NOT NULL), checksum (TEXT NOT NULL), raw_payload (JSONB), fetched_at (TIMESTAMPTZ) | PK: id, FK: source_id, UNIQUE: (source_id, external_id, adapter_version, checksum) |
| 11 | `parsed_listings` | id (TEXT PK), snapshot_id (FK → raw_snapshots UNIQUE NOT NULL), parser_version (TEXT NOT NULL), listing_price (NUMERIC(18,2)), price_currency (CHAR(3)), listing_title (TEXT), description (TEXT), parsed_attributes (JSONB), external_url (TEXT), listed_at (TIMESTAMPTZ), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: snapshot_id UNIQUE |
| 12 | `normalized_listings` | id (TEXT PK), parsed_listing_id (FK → parsed_listings UNIQUE NOT NULL), reference_id (FK → references NOT NULL), normalization_version (TEXT NOT NULL), match_confidence (NUMERIC(5,4)), match_method (TEXT), match_features (JSONB), condition (TEXT), set_status (TEXT), seller_geography (TEXT), normalized_price (NUMERIC(18,2)), normalized_currency (CHAR(3)), fx_rate (NUMERIC(18,8) NOT NULL), **fx_source (TEXT NOT NULL)**, **fx_date (DATE NOT NULL)**, **observation_at (TIMESTAMPTZ NOT NULL)**, status (listing_status NOT NULL), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: parsed_listing_id UNIQUE, reference_id |
| 13 | `duplicate_groups` | id (TEXT PK), model_version (TEXT NOT NULL), representative_id (FK → normalized_listings NOT NULL), method (TEXT), confidence (NUMERIC(5,4)), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: representative_id |
| 14 | `duplicate_group_members` | id (TEXT PK), group_id (FK → duplicate_groups NOT NULL), listing_id (FK → normalized_listings NOT NULL), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: group_id, listing_id, UNIQUE: (group_id, listing_id) |
| 15 | `valuations` | id (TEXT PK), listing_id (FK → normalized_listings NOT NULL), model_version (TEXT NOT NULL), config_version (TEXT NOT NULL), cost_assumptions_version (TEXT NOT NULL), expected_exit_price (NUMERIC(18,2)), exit_price_currency (CHAR(3)), all_in_acquisition (NUMERIC(18,2)), expected_net_resale (NUMERIC(18,2)), expected_net_profit (NUMERIC(18,2)), roi (NUMERIC(10,6)), low_estimate (NUMERIC(18,2)), high_estimate (NUMERIC(18,2)), confidence (NUMERIC(5,4)), comparable_count (INT), sample_dispersion (NUMERIC(10,4)), adjustment_details (JSONB), risk_reserve_details (JSONB), cost_breakdown (JSONB), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: listing_id |
| 16 | `opportunities` | id (TEXT PK), organization_id (FK → organizations NOT NULL), listing_id (FK → normalized_listings NOT NULL), valuation_id (FK → valuations NOT NULL), material_version (INT NOT NULL), score (NUMERIC(10,4)), state (opportunity_state NOT NULL), positive_factors (JSONB), negative_factors (JSONB), published_at (TIMESTAMPTZ), state_changed_at (TIMESTAMPTZ), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: org_id, listing_id, valuation_id, UNIQUE: (organization_id, listing_id, material_version) |
| 17 | `opportunity_views` | id (TEXT PK), opportunity_id (FK → opportunities NOT NULL), user_id (FK → users NOT NULL), viewed_at (TIMESTAMPTZ) | PK: id, FK: opportunity_id, user_id, UNIQUE: (opportunity_id, user_id) |

**ADR correction verification:**
```sql
\d normalized_listings
-- observation_at TIMESTAMPTZ NOT NULL        ← ADR-0004
-- fx_source TEXT NOT NULL                     ← ADR-0005
-- fx_date DATE NOT NULL                       ← ADR-0005
```

**Upgrade verification:**
```bash
psql -d chronoarb -c "\dt" | wc -l  # 17 tables + header (9 from 001 + 8 new)
psql -d chronoarb -c "\d normalized_listings"
psql -d chronoarb -c "\d valuations"
psql -d chronoarb -c "\d opportunities"
psql -d chronoarb -c "SELECT typname FROM pg_type WHERE typname IN ('listing_status','opportunity_state');"
```

**Downgrade verification:**
```bash
alembic downgrade -1
psql -d chronoarb -c "\dt" | wc -l  # 9 tables (back to 001 state)
```

---

### 003_alerts_and_operations

- **Revision ID:** Auto-generated by Alembic
- **Down revision:** `002_listings_and_valuation`
- **Tables:** 8
- **ENUMs created:** `delivery_status`, `feedback_decision`, `subscription_status`, `outbox_event_status`
- **ADR corrections:** ADR-0002 (alert_deliveries organization_id + material_version, no composite UNIQUE)

| # | Table | Key Columns | Constraints |
|---|-------|-------------|-------------|
| 18 | `alert_rules` | id (TEXT PK), organization_id (FK → organizations NOT NULL), created_by (FK → users NOT NULL), name (TEXT NOT NULL), filters (JSONB NOT NULL), channels (JSONB NOT NULL), cooldown_minutes (INT NOT NULL DEFAULT 60), is_enabled (BOOLEAN DEFAULT true), created_at (TIMESTAMPTZ DEFAULT NOW()), updated_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: org_id, created_by |
| 19 | `alert_deliveries` | id (TEXT PK), **organization_id (FK → organizations NOT NULL)**, rule_id (FK → alert_rules NOT NULL), user_id (FK → users NOT NULL), opportunity_id (FK → opportunities NOT NULL), **material_version (INT NOT NULL)**, channel (TEXT NOT NULL), idempotency_key (TEXT UNIQUE NOT NULL), delivery_status (delivery_status NOT NULL), provider_message_id (TEXT), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: org_id, rule_id, user_id, opp_id. **UNIQUE: idempotency_key only. NO composite UNIQUE.** |
| 20 | `feedbacks` | id (TEXT PK), organization_id (FK → organizations NOT NULL), user_id (FK → users NOT NULL), opportunity_id (FK → opportunities NOT NULL), decision (feedback_decision NOT NULL), notes (TEXT), idempotency_key (TEXT UNIQUE NOT NULL), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: org_id, user_id, opp_id, UNIQUE: idempotency_key |
| 21 | `trade_outcomes` | id (TEXT PK), organization_id (FK → organizations NOT NULL), user_id (FK → users NOT NULL), opportunity_id (FK → opportunities NULLABLE), reference_id (FK → references NOT NULL), acquisition_price (NUMERIC(18,2)), acquisition_currency (CHAR(3)), resale_price (NUMERIC(18,2)), resale_currency (CHAR(3)), actual_profit (NUMERIC(18,2)), days_to_sell (INT), idempotency_key (TEXT UNIQUE NOT NULL), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: org_id, user_id, opp_id (nullable), reference_id, UNIQUE: idempotency_key |
| 22 | `subscriptions` | id (TEXT PK), organization_id (FK → organizations NOT NULL), stripe_customer_id (TEXT), stripe_subscription_id (TEXT), status (subscription_status NOT NULL), plan_id (TEXT), current_period_start (TIMESTAMPTZ), current_period_end (TIMESTAMPTZ), trial_end (TIMESTAMPTZ), created_at (TIMESTAMPTZ DEFAULT NOW()), updated_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: org_id |
| 23 | `audit_events` | id (TEXT PK), organization_id (FK → organizations NULLABLE), user_id (FK → users NULLABLE), action (TEXT NOT NULL), resource_type (TEXT NOT NULL), resource_id (TEXT NOT NULL), details (JSONB), trace_id (TEXT), client_ip (TEXT), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, FK: org_id (nullable), user_id (nullable) |
| 24 | `outbox_events` | id (TEXT PK), event_name (TEXT NOT NULL), event_version (TEXT NOT NULL), payload (JSONB NOT NULL), trace_id (TEXT), status (outbox_event_status NOT NULL), created_at (TIMESTAMPTZ DEFAULT NOW()), published_at (TIMESTAMPTZ NULLABLE) | PK: id |
| 25 | `feature_flags` | id (TEXT PK), key (TEXT UNIQUE NOT NULL), description (TEXT), enabled (BOOLEAN DEFAULT false), organization_ids (JSONB), rollout_pct (INT DEFAULT 0), expires_at (TIMESTAMPTZ), created_at (TIMESTAMPTZ DEFAULT NOW()) | PK: id, UNIQUE: key |

**ADR correction verification:**
```sql
\d alert_deliveries
-- organization_id TEXT NOT NULL                   ← ADR-0002 D2
-- material_version INT NOT NULL                    ← ADR-0002 D3
-- idempotency_key TEXT UNIQUE NOT NULL              ← sole uniqueness constraint
-- No composite UNIQUE on (rule_id, user_id, ...)    ← ADR-0002 D1
```

**Upgrade verification:**
```bash
psql -d chronoarb -c "\dt" | wc -l  # 25 tables + header
psql -d chronoarb -c "\d alert_deliveries"
psql -d chronoarb -c "\d feeddbacks"
psql -d chronoarb -c "\d subscriptions"
psql -d chronoarb -c "SELECT typname FROM pg_type WHERE typtype='e';"  # 7 ENUMs
```

**Downgrade verification:**
```bash
alembic downgrade -1
psql -d chronoarb -c "\dt" | wc -l  # 17 tables (back to 002 state)
```

---

### 004_indexes

- **Revision ID:** Auto-generated by Alembic
- **Down revision:** `003_alerts_and_operations`
- **Tables:** 0 (index creation only)
- **ENUMs:** 0

| # | Index Name | Table | Columns | Type |
|---|-----------|-------|---------|------|
| 1 | `idx_memberships_org_user` | memberships | (organization_id, user_id) | B-tree |
| 2 | `idx_opportunities_org_state` | opportunities | (organization_id, state, published_at DESC) | B-tree |
| 3 | `idx_alert_rules_org` | alert_rules | (organization_id, is_enabled) | B-tree |
| 4 | `idx_feedbacks_org_opp` | feedbacks | (organization_id, opportunity_id) | B-tree |
| 5 | `idx_opportunities_published` | opportunities | (state, published_at DESC) WHERE state = 'published' | Partial |
| 6 | `idx_normalized_listings_ref` | normalized_listings | (reference_id, status, created_at DESC) | B-tree |
| 7 | `idx_normalized_listings_active` | normalized_listings | (status, reference_id) WHERE status = 'active' | Partial |
| 8 | `idx_alert_deliveries_idem` | alert_deliveries | (idempotency_key) | B-tree UNIQUE |
| 9 | `idx_alert_deliveries_org_user` | alert_deliveries | (organization_id, user_id, created_at DESC) | B-tree |
| 10 | `idx_alert_deliveries_opp` | alert_deliveries | (opportunity_id, material_version) | B-tree |
| 11 | `idx_feedbacks_idem` | feedbacks | (idempotency_key) | B-tree UNIQUE |
| 12 | `idx_trade_outcomes_idem` | trade_outcomes | (idempotency_key) | B-tree UNIQUE |
| 13 | `idx_outbox_pending` | outbox_events | (status, created_at) WHERE status = 'pending' | Partial |
| 14 | `idx_audit_org_time` | audit_events | (organization_id, created_at DESC) | B-tree |
| 15 | `idx_audit_resource` | audit_events | (resource_type, resource_id) | B-tree |

**Upgrade verification:**
```bash
alembic upgrade head
psql -d chronoarb -c "\di" | wc -l  # Count indexes (15+ compound + PKs)
psql -d chronoarb -c "\di idx_*"
```

**Downgrade verification:**
```bash
alembic downgrade -1
# Indexes dropped, tables remain
psql -d chronoarb -c "\dt" | wc -l  # 25 tables (still present after index downgrade)
```

---

## 5. ENUM Creation Order

ENUMs must be created **before** the tables that use them. They exist in the same migration as their first consumer table. They must be dropped **after** the tables that use them.

| Migration | ENUM | Created Before | Dropped After |
|-----------|------|---------------|---------------|
| 001 | `membership_role` (`owner`, `admin`, `dealer`, `viewer`) | `memberships` table | `memberships` table |
| 002 | `listing_status` (`active`, `quarantined`, `suppressed`, `stale`) | `normalized_listings` table | `normalized_listings` table |
| 002 | `opportunity_state` (`published`, `dismissed`, `contacted`, `purchased`, `expired`) | `opportunities` table | `opportunities` table |
| 003 | `delivery_status` (`pending`, `sent`, `failed`, `suppressed`) | `alert_deliveries` table | `alert_deliveries` table |
| 003 | `feedback_decision` (`purchased`, `contacted`, `dismissed`) | `feedbacks` table | `feedbacks` table |
| 003 | `subscription_status` (`trialing`, `active`, `past_due`, `canceled`, `unpaid`) | `subscriptions` table | `subscriptions` table |
| 003 | `outbox_event_status` (`pending`, `published`, `failed`) | `outbox_events` table | `outbox_events` table |

**ENUM creation pattern (in upgrade):**
```python
def upgrade():
    op.execute("CREATE TYPE membership_role AS ENUM ('owner', 'admin', 'dealer', 'viewer')")
    op.create_table("memberships", ..., sa.Column("role", sa.Enum("owner", "admin", "dealer", "viewer", name="membership_role", create_type=False), nullable=False), ...)
```

**ENUM drop pattern (in downgrade):**
```python
def downgrade():
    op.drop_table("memberships")
    op.execute("DROP TYPE membership_role")
```

Note: `create_type=False` prevents Alembic from auto-creating the ENUM (it's already created manually). This avoids the "type already exists" error.

---

## 6. Index Creation Strategy

### Principles

1. Indexes are created in a **separate migration** (004_indexes.py) after all 25 tables exist.
2. Index failures do not affect table data.
3. Indexes can be dropped independently of tables — `alembic downgrade -1` from 004 drops only indexes.
4. UNIQUE indexes on `idempotency_key` columns create the uniqueness constraint (not duplicating the PK).
5. Partial indexes use `WHERE` clauses and `postgresql_where=` in Alembic.

### Alembic Syntax

**Standard index:**
```python
op.create_index("idx_memberships_org_user", "memberships", ["organization_id", "user_id"])
```

**Unique index:**
```python
op.create_index("idx_alert_deliveries_idem", "alert_deliveries", ["idempotency_key"], unique=True)
```

**Partial index:**
```python
op.create_index(
    "idx_opportunities_published",
    "opportunities",
    ["state", sa.text("published_at DESC")],
    postgresql_where=sa.text("state = 'published'"),
)
```

**Downgrade:**
```python
op.drop_index("idx_memberships_org_user", table_name="memberships")
```

---

## 7. Rollback Strategy

### Full rollback path

```bash
# Reverse all 4 migrations
alembic downgrade -1  # 004 → 003 (drop 15+ indexes)
alembic downgrade -1  # 003 → 002 (drop 8 alert/operations tables + 4 ENUMs)
alembic downgrade -1  # 002 → 001 (drop 8 listing/valuation tables + 2 ENUMs)
alembic downgrade -1  # 001 → None (drop 9 identity/catalog tables + 1 ENUM)

# Verify: empty database
psql -d chronoarb -c "\dt"         # No tables
psql -d chronoarb -c "SELECT typname FROM pg_type WHERE typtype='e';"  # No ENUMs
```

### Full re-upgrade

```bash
alembic upgrade head  # Re-applies all 4 migrations
alembic current       # → 004_indexes (head)
psql -d chronoarb -c "\dt" | wc -l  # 25 tables + header
```

### Partial rollback strategies

| Goal | Command | Effect |
|------|---------|--------|
| Remove indexes only | `alembic downgrade -1` (from 004) | Drops 15+ indexes, keeps all tables |
| Remove alert/ops tables | `alembic downgrade 002_listings_and_valuation` | Drops 003 + 004 |
| Remove listing/valuation tables | `alembic downgrade 001_identity_and_catalog` | Drops 002 + 003 + 004 |
| Full reset | `alembic downgrade base` | Drops everything |

### Database reset

```bash
docker stop chronoarb-pg && docker rm chronoarb-pg
docker run -d --name chronoarb-pg -p 5432:5432 \
  -e POSTGRES_PASSWORD=chronoarb \
  -e POSTGRES_DB=chronoarb \
  postgres:17
sleep 3
CHRONOARB_DATABASE_URL=postgresql+asyncpg://postgres:chronoarb@localhost:5432/chronoarb \
  alembic upgrade head
```

---

## 8. Verification Commands

### Pre-migration (before any migration runs)

```bash
alembic current
# → No current revision — database is empty
psql -d chronoarb -c "\dt"
# → No tables
```

### Per-migration (after each)

```bash
# After 001
psql -d chronoarb -c "\dt" | wc -l                                    # 9 tables
psql -d chronoarb -c "\d organizations"
psql -d chronoarb -c "\d memberships"
psql -d chronoarb -c "SELECT typname FROM pg_type WHERE typname='membership_role';"

# After 002
psql -d chronoarb -c "\dt" | wc -l                                    # 17 tables
psql -d chronoarb -c "\d normalized_listings"                         # Verify observation_at, fx_source, fx_date
psql -d chronoarb -c "\d valuations"                                  # Verify NUMERIC types
psql -d chronoarb -c "SELECT typname FROM pg_type WHERE typtype='e';" # 3 ENUMs

# After 003
psql -d chronoarb -c "\dt" | wc -l                                    # 25 tables
psql -d chronoarb -c "\d alert_deliveries"                            # Verify org_id + material_version, NO composite UNIQUE
psql -d chronoarb -c "\d subscriptions"
psql -d chronoarb -c "SELECT typname FROM pg_type WHERE typtype='e';" # 7 ENUMs

# After 004
psql -d chronoarb -c "\di" | wc -l                                    # Index count
psql -d chronoarb -c "\di idx_*"                                      # List all indexes
```

### Full downgrade + re-upgrade

```bash
alembic downgrade base    # All 4 reversed
psql -d chronoarb -c "\dt" | wc -l                                    # 0 (empty)
psql -d chronoarb -c "SELECT typname FROM pg_type WHERE typtype='e';" # 0 (no ENUMs)
alembic upgrade head      # All 4 re-applied
psql -d chronoarb -c "\dt" | wc -l                                    # 25 tables
alembic current           # → 004_indexes (head)
```

### Fast local verification

```bash
make db-test-pg
# or:
docker exec chronoarb-pg psql -U postgres -d chronoarb -c "\dt"
```

---

## 9. ADR Compliance Checklist

| ADR | Requirement | Migration | Verify |
|-----|-------------|-----------|--------|
| ADR-0001 D2 | PostgreSQL sole source of record | All tables | `\dt` |
| ADR-0001 D3 | NUMERIC for money | 002 (parsed_listings, normalized_listings, valuations, opportunities) | `\d valuations` |
| ADR-0001 D4 | TEXT PKs (ULID) | All tables | `\d organizations` |
| ADR-0001 D7 | organization_id on tenant tables | 001/002/003 (10 tables) | `\d opportunities`, `\d alert_deliveries` |
| ADR-0002 D1 | No composite UNIQUE on alert_deliveries | 003 | `\d alert_deliveries` |
| ADR-0002 D2 | organization_id on alert_deliveries | 003 | `\d alert_deliveries` |
| ADR-0002 D3 | material_version on alert_deliveries | 003 | `\d alert_deliveries` |
| ADR-0004 D1 | observation_at on normalized_listings | 002 | `\d normalized_listings` |
| ADR-0005 D1 | fx_source + fx_date on normalized_listings | 002 | `\d normalized_listings` |
| ADR-0008 | 4 migrations split by domain | 001/002/003/004 | `alembic history` |

---

## 10. Development Workflow

### Authoring Order

```
DB-06 (001) → DB-07 (002) → DB-08 (003) → DB-09 (004)
```

DB-06, DB-07, and DB-08 are independent (different tables) and can be written in parallel. DB-09 depends on all three being applied first (needs tables to exist for indexes).

### Writing a migration

1. Write `upgrade()` function with `op.create_table()` and `op.execute("CREATE TYPE ...")`
2. Write `downgrade()` function with `op.drop_table()` and `op.execute("DROP TYPE ...")` in reverse order
3. Run `alembic upgrade head` against local SQLite (verifies no Python syntax errors)
4. Review against database-design.md column-by-column
5. Commit

### Testing a migration

1. `alembic downgrade base` (reset)
2. `alembic upgrade head` (apply all)
3. `psql ... \dt` (verify count)
4. Verify ADR-specific columns
5. `alembic downgrade base` (reset again)
6. `alembic upgrade head` (re-apply — idempotency test)
