# ADR-0004: Customer-Visible Data Freshness Model

**Status:** Accepted
**Date:** 2026-08-03
**Deciders:** Lead Software Architect
**Supersedes:** None
**Resolves:** Architecture Review MAJOR-01, MAJOR-06

---

## Context

AGENTS.md §2 requires: "Customer-visible estimates must include data age, confidence, valuation version, and the cost-assumption version."

The current database design includes `valuations.confidence`, `valuations.model_version`, and `valuations.cost_assumptions_version`, satisfying three of the four requirements. However, "data age" — the elapsed time since the listing was observed at its source — is not explicitly stored or surfaced in any API response schema.

The observation timestamp exists deep in the data lineage: `raw_snapshots.fetched_at` → `parsed_listings` → `normalized_listings` → `valuations` → `opportunities`. Computing data age at query time requires traversing 4 JOINs, which is expensive for the opportunity feed (a frequently-accessed, paginated endpoint).

---

## Problem

### P1: data_age not in API responses

Customer-visible estimates (opportunity detail, opportunity feed cards) do not include data age, violating AGENTS.md §2.

### P2: Deep JOIN chain for a frequently-needed value

The observation timestamp originates at `raw_snapshots.fetched_at`. Computing data age for a feed of 50 opportunities requires:
```sql
SELECT opportunities.*, raw_snapshots.fetched_at
FROM opportunities
JOIN valuations ON opportunities.valuation_id = valuations.id
JOIN normalized_listings ON valuations.listing_id = normalized_listings.id
JOIN parsed_listings ON normalized_listings.parsed_listing_id = parsed_listings.id
JOIN raw_snapshots ON parsed_listings.snapshot_id = raw_snapshots.id
```

This 4-JOIN chain is expensive for paginated feed queries displayed to every dealer on every page load.

### P3: Two possible observation timestamps

There are two time sources for "when was this listing observed":
1. `raw_snapshots.fetched_at` — When ChronoArb's worker fetched the listing (always available, controlled by us)
2. `parsed_listings.listed_at` — When the source claims the listing was posted (may be missing, inaccurate, or in source-local timezone)

The choice between them affects data age accuracy and how it's presented to users.

---

## Decision

### D1: Denormalize `observation_at` into normalized_listings

Add `observation_at TIMESTAMPTZ NOT NULL` to `normalized_listings`, populated at normalization time as:

```
observation_at = COALESCE(parsed_listings.listed_at, raw_snapshots.fetched_at)
```

**Rationale:**
- Prefer `listed_at` when available because it represents the actual listing time (closer to true data age).
- Fall back to `fetched_at` when `listed_at` is missing or unparseable (always available).
- Denormalizing into `normalized_listings` eliminates 3 of the 4 JOINs for feed queries. Only `opportunities → valuations → normalized_listings` remains (2 JOINs).

### D2: Compute `data_age` in API layer, not database

`data_age` shall be computed as a virtual field in the API response layer:

```
data_age_seconds = (NOW() - normalized_listings.observation_at).total_seconds()
```

It is NOT stored as a column because:
- It changes with every passing second (would require constant updates).
- It is trivially computable from `observation_at` + current time.
- Storing it would create a cache invalidation problem.

### D3: Include all four required fields in opportunity response schemas

Every customer-visible opportunity response shall include:

| Field | Source | Format |
|-------|--------|--------|
| `data_age_seconds` | `NOW() - observation_at` | Integer, seconds |
| `confidence` | `valuations.confidence` | Number, 0.0–1.0, 4 decimal places |
| `valuation_version` | `valuations.model_version` | String |
| `cost_assumptions_version` | `valuations.cost_assumptions_version` | String |

For the opportunity feed (list view), include all four fields. For the opportunity detail view, additionally include `observation_at` as an RFC 3339 timestamp.

### D4: Surface data age visually as a human-readable duration

The API returns `data_age_seconds` as a machine-readable integer. The client (web/mobile) formats this as a human-readable duration (e.g., "2 minutes ago", "3 hours ago", "1 day ago") and displays it prominently near the listing price.

---

## Alternatives Considered

### Alternative A: Compute data_age at query time without denormalization

Keep `observation_at` deep in the lineage chain and compute it with a 4-JOIN query.

**Rejected because:** Expensive for the opportunity feed (paginated, sorted, filtered). The feed is one of the most frequently accessed queries. Paying a 4-JOIN cost on every feed page load is not justified when denormalization is simple and stable.

### Alternative B: Store data_age as a column (pre-computed duration)

Store `data_age_seconds INTEGER` and update it periodically.

**Rejected because:** Requires a background job to update the column. Data is stale between updates. The computation `NOW() - observation_at` is trivial and fast. Pre-computing a value that changes every second is an anti-pattern.

### Alternative C: Use `raw_snapshots.fetched_at` exclusively

Always use the ChronoArb fetch time, ignoring `parsed_listings.listed_at`.

**Rejected because:** If the source provides a reliable `listed_at` timestamp, using it gives a more accurate picture of how long the listing has been on the market. The "3 hours ago" listing vs "3 hours ago we fetched it" are meaningfully different to a dealer. The COALESCE approach gives the best available data.

### Alternative D: Store `observation_at` in valuations instead of normalized_listings

**Rejected because:** `observation_at` is a property of the listing observation, not the valuation. Mixing it into the valuation table creates coupling between unrelated concepts. The normalized listing is the correct entity to carry observation metadata.

---

## Consequences

### Positive

- AGENTS.md §2 compliance: all four required fields are present in customer-visible estimates.
- Feed queries are efficient (2 JOINs instead of 4).
- `data_age` is always current (computed at request time).
- Both web and mobile get `data_age_seconds` without additional logic.
- Human-readable formatting is a pure client concern (separation of concerns).

### Negative

- `observation_at` is denormalized from deeper lineage tables. If the source data is later corrected, `normalized_listings` needs updating. Since `normalized_listings` are immutable (ADR-0001 D10), corrections create new versions, which naturally carry the corrected `observation_at`.
- Two timestamps (`created_at` = when normalized, `observation_at` = when observed) on `normalized_listings` may cause initial confusion. Clear documentation in the schema is required.

### Neutral

- The COALESCE logic means that `data_age` may be based on `fetched_at` for some sources and `listed_at` for others. The API can optionally expose a `data_age_source` field (`"source_listed"` | `"chronoarb_fetched"`) for transparency.

---

## Migration Impact

### New migration (Week 1-2, initial schema):

```sql
ALTER TABLE normalized_listings
ADD COLUMN observation_at TIMESTAMPTZ NOT NULL;
```

The column is populated at normalization time by the normalization worker. No backfill needed for greenfield.

### No API contract changes needed:
- `data_age_seconds` is an additive field in opportunity responses.
- Existing consumers ignore unknown fields (standard JSON behavior).

---

## Testing Implications

### Domain tests
- `compute_data_age(observation_at, now)` returns correct integer seconds.
- `determine_observation_at(listed_at, fetched_at)` returns `listed_at` when non-null, `fetched_at` otherwise.
- Zero and negative `data_age_seconds` are handled (clock skew between source and server).

### Integration tests
- Normalization worker populates `observation_at` correctly from lineage data.
- API response includes all four required fields with correct values.
- Feed response includes `data_age_seconds` for each opportunity.

### Contract tests
- OpenAPI schema validates that `data_age_seconds`, `confidence`, `valuation_version`, and `cost_assumptions_version` are present in opportunity responses.
- Breaking change detection flags if any of the four fields are removed.

### Property-based tests
- `data_age_seconds >= 0` for any valid `observation_at` (assuming server clock ≥ observation clock, with tolerance for minor skew).

---

## References

- AGENTS.md §2: "Customer-visible estimates must include data age, confidence, valuation version, and the cost-assumption version."
- ADR-0001 D10: Immutable Evidence and Versioned Outputs
- database-design.md §2.4: normalized_listings table
- database-design.md §2.6: valuations table
- api-design.md §3.3: Opportunities API
- Architecture Review: MAJOR-01, MAJOR-06
