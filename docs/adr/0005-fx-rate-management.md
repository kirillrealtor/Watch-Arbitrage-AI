# ADR-0005: FX Rate Management

**Status:** Accepted
**Date:** 2026-08-03
**Deciders:** Lead Software Architect
**Supersedes:** None
**Resolves:** Architecture Review MAJOR-02

---

## Context

The normalization worker converts listing prices from source currencies to a base currency (the organization's configured currency) using foreign exchange rates. The current database design stores only `fx_rate NUMERIC(18,8)` on `normalized_listings` without recording:
- Which provider or service supplied the rate (source)
- When the rate was obtained (date)
- Whether it's a live rate, daily close, or fixed rate

ADR-0001 D10 mandates that "all pipeline outputs shall be immutable records with explicit version fields" and the playbook requires that "every output explicitly names the method and version." An FX rate without provenance violates the version-everything principle.

Financial correctness requires auditability: if a valuation produces incorrect profit calculations due to a bad FX rate, operators must be able to identify which rate was used, when, and from which source.

---

## Problem

### P1: No FX rate provenance

`normalized_listings.fx_rate` is a bare number. There is no way to:
- Identify which FX provider supplied the rate
- Determine when the rate was obtained
- Reproduce the normalization using the same rate
- Audit incorrect valuations caused by stale or erroneous rates

### P2: No explicit FX rate versioning policy

The SRS and playbook do not specify:
- Which FX rate source to use
- Whether to use live rates, daily rates, or snapshot rates
- What precision to store
- How frequently to refresh
- Whether to use bid/ask/mid rates

---

## Decision

### D1: Add FX rate provenance columns

Add two columns to `normalized_listings`:

```sql
fx_rate       NUMERIC(18,8) NOT NULL    -- Exchange rate (e.g., EUR/USD = 1.08500000)
fx_source     TEXT NOT NULL              -- Provider identifier (e.g., "ecb", "openexchange", "fixer")
fx_date       DATE NOT NULL              -- Date the rate is valid for (not when it was fetched)
```

**Rationale:**
- `fx_source` enables auditability and operator identification of rate issues.
- `fx_date` captures which day's rate was used (daily rates are common for FX; intraday rates would use TIMESTAMPTZ).
- Using `DATE` rather than `TIMESTAMPTZ` is intentional: FX rates are typically published as daily rates (ECB fixing, end-of-day). This can be changed to `TIMESTAMPTZ` if live intraday rates are needed.
- All three columns together enable full reproducibility: given the same source + date + rate, the normalization produces the same normalized price.

### D2: Use a single, named FX rate provider with a defined schedule

For MVP, use one FX rate provider with a defined refresh schedule:

| Parameter | MVP Value |
|-----------|-----------|
| Provider | AWS Currency Converter (free tier) or ECB reference rates (free, no API key) |
| Rate type | Daily reference rate (mid-rate) |
| Refresh | Once per day at 00:05 UTC |
| Precision | 8 decimal places (`NUMERIC(18,8)`) |
| Fallback | Previous day's rate if provider is unavailable |

**Rationale for single provider:** Multi-provider FX is over-engineering for MVP. A single, auditable source with documented fallback behavior is sufficient. If accuracy becomes a concern in v1.1, add a second provider for cross-verification.

**Rationale for daily rates:** Listing arbitrage operates on multi-hour or multi-day timescales. Intraday FX fluctuations are noise relative to the valuation's other uncertainty factors (condition, set completeness, time-to-sale). Daily rates are appropriate for the use case.

### D3: Store the rate, not a calculation derived from the rate

The `normalized_price` field is the rate-applied price: `listing_price * fx_rate`. The rate is stored alongside it, not embedded in the calculation. This separates the input (rate) from the output (normalized price) for auditability.

### D4: FX rate gateway as a typed interface

FX rate retrieval shall be behind a typed gateway interface in `packages/domain-python/`:

```python
class FxRateProvider(Protocol):
    async def get_rate(self, from_currency: str, to_currency: str, date: date) -> Decimal:
        ...
```

The normalization worker injects the provider, enabling:
- Easy testing with mock rates
- Provider substitution without changing normalization logic
- Rate retrieval with explicit date (not just "current rate")

---

## Alternatives Considered

### Alternative A: Store `fx_rate` only, no provenance (rejected)

**Rejected because:** Violates ADR-0001 D10 (version everything). Makes audits impossible. Cannot reproduce normalizations.

### Alternative B: Store `fx_rate_id` referencing a separate FX rates table (rejected)

A separate `fx_rates` table with a foreign key:

```sql
fx_rates
├── id, source, from_currency, to_currency, rate, date

normalized_listings.fx_rate_id FK → fx_rates.id
```

**Rejected because:** Adds a separate table and JOIN for a relatively stable, low-cardinality dataset. The normalization time is close to the rate date. Denormalizing `fx_source`, `fx_date`, and `fx_rate` directly into `normalized_listings` is simpler and avoids the extra table at the cost of ~50 bytes per row.

**Revisit if:** FX rate data is needed for other purposes (analytics, cost dashboards) that justify a shared table. The column values can be migrated into a dedicated table later via expand/contract.

### Alternative C: Live intraday FX rates (rejected)

**Rejected because:** Adds complexity (WebSocket to FX provider, rate refresh logic, intraday volatility handling). Intraday FX is noise relative to other valuation uncertainties. A daily rate is sufficient for the use case.

### Alternative D: No FX gateway abstraction (rejected)

**Rejected because:** AGENTS.md §9 requires "External calls are behind typed gateways/adapters and are mocked through interfaces in tests." FX rate retrieval is an external call. Without a gateway, normalization tests would depend on a live FX provider.

---

## Consequences

### Positive

- Full FX rate auditability: trace any normalized price back to its source rate.
- Reproducible normalizations: same listing + same rate = same normalized price.
- Gateway interface enables testable, mockable FX retrieval.
- Single provider keeps operational complexity low for MVP.
- Daily rate schedule aligns with the use case's timescale.

### Negative

- Three additional columns per `normalized_listings` row (~50 bytes per row).
- Daily rates mean a listing normalized at 23:59 may use a rate that is 23 hours and 54 minutes old. This is acceptable given the valuation's other uncertainties.
- Single provider creates a single point of dependency. Mitigated by fallback to previous day's rate.

### Neutral

- The FX gateway pattern can be extended to multiple providers in v1.1 without changing the `normalized_listings` schema (just the `fx_source` value).

---

## Migration Impact

### New migration (Week 1-2, initial schema):

```sql
ALTER TABLE normalized_listings
ADD COLUMN fx_source TEXT NOT NULL,
ADD COLUMN fx_date DATE NOT NULL;
```

The `fx_rate` column already exists. All three columns are populated at normalization time.

### No backfill needed (greenfield).

---

## Testing Implications

### Domain tests
- `FxRateProvider.get_rate("EUR", "USD", date)` returns expected value for known test date.
- Gateway correctly calls the configured provider.
- Fallback to previous day's rate when provider is unavailable.

### Contract tests
- FX gateway mock returns consistent rates for tests.
- Normalization tests use mocked FX gateway, not live provider.

### Integration tests
- `normalized_listings` row contains correct `fx_source`, `fx_date`, and `fx_rate` after normalization.
- Normalized price equals `listing_price * fx_rate` within Decimal precision.

### Property-based tests
- For any positive `listing_price` and `fx_rate > 0`, `normalized_price > 0`.
- `fx_rate` precision is exactly 8 decimal places (not more).

---

## References

- ADR-0001 D10: Immutable Evidence and Versioned Outputs
- ADR-0001 D3: Decimal/Fixed-Point for All Financial Values
- AGENTS.md §9: FastAPI and Python Rules (gateway pattern)
- database-design.md §2.4: normalized_listings table
- worker-design.md §3.3: Normalization Worker
- Architecture Review: MAJOR-02
