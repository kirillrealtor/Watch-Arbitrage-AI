# ChronoArb — Database Design

**Document type:** Database schema and entity design
**Source:** ChronoArb_MVP_SRS_v1.0 §11, AI-Agent Engineering Playbook §13
**Date:** 2026-08-03

---

## 1. Database Principles

- **PostgreSQL 18** on AWS RDS is the single system of record.
- Redis/Valkey stores only short-lived cache, rate counters, locks, and WebSocket fanout — never authoritative state.
- All financial values use `NUMERIC(precision, scale)` with explicit `CHAR(3)` ISO 4217 currency codes.
- All timestamps are UTC (`TIMESTAMPTZ`).
- All primary keys use opaque ULID-style identifiers (e.g., `org_01J...`) for multi-tenant safety and sortability.
- Organization-scoped tables include `organization_id` column with composite indexes.

---

## 2. Entity Model

### 2.1 Identity and Organizations

```
organizations
├── id (PK)            ULID, e.g. org_...
├── name               TEXT NOT NULL
├── slug               TEXT UNIQUE NOT NULL
├── settings           JSONB (timezone, default_currency, fee_defaults)
├── created_at         TIMESTAMPTZ
└── updated_at         TIMESTAMPTZ

users
├── id (PK)            ULID
├── cognito_sub        TEXT UNIQUE NOT NULL
├── email              TEXT UNIQUE NOT NULL
├── display_name       TEXT
├── created_at         TIMESTAMPTZ
└── updated_at         TIMESTAMPTZ

memberships
├── id (PK)            ULID
├── organization_id    FK → organizations.id
├── user_id            FK → users.id
├── role               ENUM(owner, admin, dealer, viewer)
├── invited_by         FK → users.id (nullable)
├── created_at         TIMESTAMPTZ
└── UNIQUE(user_id, organization_id)
```

### 2.2 Catalog

```
brands
├── id (PK)            ULID
├── name               TEXT UNIQUE NOT NULL
├── slug               TEXT UNIQUE NOT NULL
├── created_at         TIMESTAMPTZ

references  (canonical watch references)
├── id (PK)            ULID
├── brand_id           FK → brands.id
├── ref_code           TEXT NOT NULL     (e.g. "116610LN")
├── model_name         TEXT              (e.g. "Submariner Date")
├── generation         TEXT
├── attributes         JSONB            (material, dial, bezel, bracelet, movement, case_size)
├── is_active          BOOLEAN DEFAULT true
├── created_at         TIMESTAMPTZ
└── UNIQUE(brand_id, ref_code)

aliases
├── id (PK)            ULID
├── reference_id       FK → references.id
├── alias_text         TEXT NOT NULL
├── source             TEXT             (source_key or "manual")
└── UNIQUE(alias_text, source)

watch_lists
├── id (PK)            ULID
├── organization_id    FK → organizations.id
├── name               TEXT NOT NULL
├── created_at         TIMESTAMPTZ

watch_list_entries
├── id (PK)            ULID
├── watch_list_id      FK → watch_lists.id
├── reference_id       FK → references.id
└── UNIQUE(watch_list_id, reference_id)
```

### 2.3 Sources and Ingestion

```
sources
├── id (PK)            ULID
├── source_key         TEXT UNIQUE NOT NULL
├── display_name       TEXT NOT NULL
├── adapter_version    TEXT NOT NULL
├── access_mode        TEXT NOT NULL      (api, feed, permissioned_public)
├── rate_policy        JSONB              (max_concurrent, requests_per_second, daily_quota)
├── approval_ref       TEXT               (legal/business approval record)
├── is_enabled         BOOLEAN DEFAULT false
├── created_at         TIMESTAMPTZ

raw_snapshots
├── id (PK)            ULID
├── source_id          FK → sources.id
├── external_id        TEXT NOT NULL
├── adapter_version    TEXT NOT NULL
├── checksum           TEXT NOT NULL
├── raw_payload        JSONB              (or S3 key reference)
├── fetched_at         TIMESTAMPTZ
└── UNIQUE(source_id, external_id, adapter_version, checksum)
```

### 2.4 Listings and Normalization

```
parsed_listings
├── id (PK)            ULID
├── snapshot_id        FK → raw_snapshots.id UNIQUE
├── parser_version     TEXT NOT NULL
├── listing_price      NUMERIC(18,2)
├── price_currency     CHAR(3)
├── listing_title      TEXT
├── description        TEXT
├── parsed_attributes  JSONB              (condition_text, set_info, year, location, seller_name, etc.)
├── external_url       TEXT
├── listed_at          TIMESTAMPTZ
├── created_at         TIMESTAMPTZ

normalized_listings
├── id (PK)            ULID
├── parsed_listing_id  FK → parsed_listings.id UNIQUE
├── reference_id       FK → references.id
├── normalization_version TEXT NOT NULL
├── match_confidence   NUMERIC(5,4)       (0.0-1.0)
├── match_method       TEXT               (exact, alias, variant_rule, classifier)
├── match_features     JSONB
├── condition          TEXT               (new, pre_owned, unknown, etc.)
├── set_status         TEXT               (full_set, box_only, watch_only, unknown)
├── seller_geography   TEXT
├── normalized_price   NUMERIC(18,2)      (in base currency)
├── normalized_currency CHAR(3)
├── fx_rate            NUMERIC(18,8)
├── status             ENUM(active, quarantined, suppressed, stale)
└── created_at         TIMESTAMPTZ
```

### 2.5 Duplicates

```
duplicate_groups
├── id (PK)            ULID
├── model_version      TEXT NOT NULL
├── representative_id  FK → normalized_listings.id
├── method             TEXT
├── confidence         NUMERIC(5,4)
└── created_at         TIMESTAMPTZ

duplicate_group_members
├── id (PK)            ULID
├── group_id           FK → duplicate_groups.id
├── listing_id         FK → normalized_listings.id
└── UNIQUE(group_id, listing_id)
```

### 2.6 Valuation

```
valuations
├── id (PK)            ULID
├── listing_id         FK → normalized_listings.id
├── model_version      TEXT NOT NULL
├── config_version     TEXT NOT NULL
├── cost_assumptions_version TEXT NOT NULL
├── expected_exit_price    NUMERIC(18,2)
├── exit_price_currency    CHAR(3)
├── all_in_acquisition     NUMERIC(18,2)
├── expected_net_resale    NUMERIC(18,2)
├── expected_net_profit    NUMERIC(18,2)
├── roi                   NUMERIC(10,6)
├── low_estimate          NUMERIC(18,2)
├── high_estimate         NUMERIC(18,2)
├── confidence            NUMERIC(5,4)
├── comparable_count      INT
├── sample_dispersion     NUMERIC(10,4)
├── adjustment_details    JSONB
├── risk_reserve_details  JSONB
├── cost_breakdown        JSONB
└── created_at            TIMESTAMPTZ
```

### 2.7 Opportunities

```
opportunities
├── id (PK)            ULID
├── organization_id    FK → organizations.id
├── listing_id         FK → normalized_listings.id
├── valuation_id       FK → valuations.id
├── material_version   INT NOT NULL
├── score              NUMERIC(10,4)
├── state              ENUM(published, dismissed, contacted, purchased, expired)
├── positive_factors   JSONB
├── negative_factors   JSONB
├── published_at       TIMESTAMPTZ
├── state_changed_at   TIMESTAMPTZ
└── UNIQUE(organization_id, listing_id, material_version)

opportunity_views
├── id (PK)            ULID
├── opportunity_id     FK → opportunities.id
├── user_id            FK → users.id
├── viewed_at          TIMESTAMPTZ
└── UNIQUE(opportunity_id, user_id)
```

### 2.8 Alerts

```
alert_rules
├── id (PK)            ULID
├── organization_id    FK → organizations.id
├── created_by         FK → users.id
├── name               TEXT NOT NULL
├── filters            JSONB NOT NULL      (reference_ids, min_profit, max_acquisition, conditions)
├── channels           JSONB NOT NULL      ([{type: telegram, id: ...}, {type: push}])
├── cooldown_minutes   INT NOT NULL DEFAULT 60
├── is_enabled         BOOLEAN DEFAULT true
├── created_at         TIMESTAMPTZ
└── updated_at         TIMESTAMPTZ

alert_deliveries
├── id (PK)            ULID
├── rule_id            FK → alert_rules.id
├── user_id            FK → users.id
├── opportunity_id     FK → opportunities.id
├── channel            TEXT NOT NULL       (telegram, push)
├── idempotency_key    TEXT UNIQUE NOT NULL
├── delivery_status    ENUM(pending, sent, failed, suppressed)
├── provider_message_id TEXT
├── created_at         TIMESTAMPTZ
└── UNIQUE(rule_id, user_id, opportunity_id, channel, material_version)
```

### 2.9 Feedback and Outcomes

```
feedbacks
├── id (PK)            ULID
├── organization_id    FK → organizations.id
├── user_id            FK → users.id
├── opportunity_id     FK → opportunities.id
├── decision           ENUM(purchased, contacted, dismissed)
├── notes              TEXT
├── idempotency_key    TEXT UNIQUE NOT NULL
├── created_at         TIMESTAMPTZ

trade_outcomes
├── id (PK)            ULID
├── organization_id    FK → organizations.id
├── user_id            FK → users.id
├── opportunity_id     FK → opportunities.id (nullable)
├── reference_id       FK → references.id
├── acquisition_price  NUMERIC(18,2)
├── acquisition_currency CHAR(3)
├── resale_price       NUMERIC(18,2)
├── resale_currency    CHAR(3)
├── actual_profit      NUMERIC(18,2)
├── days_to_sell       INT
├── idempotency_key    TEXT UNIQUE NOT NULL
└── created_at         TIMESTAMPTZ
```

### 2.10 Billing

```
subscriptions
├── id (PK)            ULID
├── organization_id    FK → organizations.id
├── stripe_customer_id TEXT
├── stripe_subscription_id TEXT
├── status             ENUM(trialing, active, past_due, canceled, unpaid)
├── plan_id            TEXT
├── current_period_start TIMESTAMPTZ
├── current_period_end   TIMESTAMPTZ
├── trial_end          TIMESTAMPTZ
├── created_at         TIMESTAMPTZ
└── updated_at         TIMESTAMPTZ
```

### 2.11 Operations and Audit

```
audit_events
├── id (PK)            ULID
├── organization_id    FK → organizations.id (nullable)
├── user_id            FK → users.id (nullable)
├── action             TEXT NOT NULL
├── resource_type      TEXT NOT NULL
├── resource_id        TEXT NOT NULL
├── details            JSONB
├── trace_id           TEXT
├── client_ip          TEXT
├── created_at         TIMESTAMPTZ

outbox_events
├── id (PK)            ULID
├── event_name         TEXT NOT NULL
├── event_version      TEXT NOT NULL
├── payload            JSONB NOT NULL
├── trace_id           TEXT
├── status             ENUM(pending, published, failed)
├── created_at         TIMESTAMPTZ
└── published_at       TIMESTAMPTZ (nullable)
```

### 2.12 Feature Flags

```
feature_flags
├── id (PK)            ULID
├── key                TEXT UNIQUE NOT NULL
├── description        TEXT
├── enabled            BOOLEAN DEFAULT false
├── organization_ids   JSONB              (null = all, array = specific orgs)
├── rollout_pct        INT DEFAULT 0
├── expires_at         TIMESTAMPTZ
└── created_at         TIMESTAMPTZ
```

---

## 3. Key Indexes

All indexes must be verified against EXPLAIN ANALYZE plans for real query paths.

```sql
-- Organization-scoped lookups (composite indexes)
CREATE INDEX idx_memberships_org_user ON memberships(organization_id, user_id);
CREATE INDEX idx_opportunities_org_state ON opportunities(organization_id, state, published_at DESC);
CREATE INDEX idx_alert_rules_org ON alert_rules(organization_id, is_enabled);
CREATE INDEX idx_feedbacks_org_opp ON feedbacks(organization_id, opportunity_id);

-- Feed query paths
CREATE INDEX idx_opportunities_published ON opportunities(state, published_at DESC)
  WHERE state = 'published';
CREATE INDEX idx_normalized_listings_ref ON normalized_listings(reference_id, status, created_at DESC);

-- Alert matching
CREATE INDEX idx_normalized_listings_active ON normalized_listings(status, reference_id)
  WHERE status = 'active';

-- Idempotency lookups
CREATE INDEX idx_alert_deliveries_idem ON alert_deliveries(idempotency_key);
CREATE INDEX idx_feedbacks_idem ON feedbacks(idempotency_key);
CREATE INDEX idx_trade_outcomes_idem ON trade_outcomes(idempotency_key);

-- Outbox publishing
CREATE INDEX idx_outbox_pending ON outbox_events(status, created_at)
  WHERE status = 'pending';

-- Audit queries
CREATE INDEX idx_audit_org_time ON audit_events(organization_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_events(resource_type, resource_id);
```

---

## 4. Migration Policy

All migrations follow the **expand/contract** pattern:

1. **Expand** — Add nullable columns, tables, or indexes. No destructive changes.
2. **Deploy compatible code** — Application reads/writes both shapes during rollout.
3. **Backfill** — Resumable, observable, rate-limited job with checkpoints.
4. **Cut over** — Enable new path with flag/config; verify metrics.
5. **Contract** — Remove old structures in a later release after compatibility window passes.

Migrations are **forward-only** in production. Every migration has a staging rehearsal and documented recovery strategy. Application rollback must remain possible until cutover is verified.

---

## 5. Entity Relationship Diagram (Key Relationships)

```
organizations ──< memberships >── users
     │
     ├──< watch_lists >──< watch_list_entries >── references
     │                                                │
     │                                    brands ─────┘
     │                                    aliases ────┘
     │
     ├──< opportunities ──< alert_deliveries >── alert_rules
     │        │                                         │
     │        ├── valuations ──── normalized_listings ──┘
     │        │                       │
     │        │                  parsed_listings
     │        │                       │
     │        │                  raw_snapshots
     │        │                       │
     │        │                  sources
     │        │
     │        ├── duplicate_groups >── duplicate_group_members
     │        │
     │        ├── feedbacks
     │        └── opportunity_views
     │
     ├──< trade_outcomes
     ├──< subscriptions
     └──< audit_events
```

---

## 6. Partitioning

No table partitioning at MVP. Partition only where evidence from production query plans and data volumes shows operational benefit. Avoid early partition complexity as stated in the playbook §13.1.
