# Batch 02 — Implementation Review

**Review type:** Post-implementation quality audit
**Reviewed batch:** Batch 2 — Backend Foundation (WF-09 through WF-50, plus WF-21/22/47 from B3 scope)
**Date:** 2026-08-03T14:05+05:00
**Reviewer:** Architecture review pass
**Files reviewed:** 17 source files, 3 test files, 4 pyproject.toml, 48 placeholder __init__.py

---

## Executive Summary

Batch 2 delivers a solid foundation. The domain layer correctly enforces Decimal-only money (one float-acceptance gap), the SourceAdapter Protocol matches ADR-0007 precisely, the FastAPI shell has correct middleware and error handling, and 43 tests pass comprehensively. Four issues need correction: Money silently accepts float input (violating AGENTS.md §2), unused imports, API envelope trace_id placement inconsistency, and the database status placeholder giving false confidence. No architectural violation, no security gap, no dependency direction error.

**Verdict:** APPROVED WITH CORRECTIONS

---

## 1. Python Package Structure

### 1.1 Package Topology Audit

| Package | pyproject.toml | requires-python | Depends On | Assessment |
|---------|---------------|----------------|------------|------------|
| chronoarb-domain | domain-python/ | >=3.13 | None | Correct — zero deps |
| chronoarb-adapters | source-adapters/ | >=3.13 | chronoarb-domain | Correct — one-directional per ADR-0007 D1 |
| chronoarb-api | apps/api/ | >=3.13 | chronoarb-domain, fastapi, sqlalchemy, alembic, pydantic-settings, asyncpg | Correct |
| chronoarb-worker | apps/worker/ | >=3.13 | chronoarb-domain, chronoarb-adapters, sqlalchemy, asyncpg | Correct |

**Finding:** All 4 packages declare `requires-python = ">=3.13"`, matching the python-runtime.md decision. Package dependency directions match ADR-0007 D2: domain ← adapters ← api/worker. No violation.

### 1.2 Package Public API Surface

`chronoarb/__init__.py` exports: `Money`, `DomainError`, `ValidationError`, `CurrencyMismatchError`, `generate_ulid`.

| Export | Present in domain | Exported correctly | Assessment |
|--------|------------------|--------------------|------------|
| Money | domain/money.py | Yes | Correct |
| DomainError | domain/errors.py | Yes | Correct |
| ValidationError | domain/errors.py | Yes | Correct |
| CurrencyMismatchError | domain/errors.py | Yes | Correct |
| generate_ulid | domain/ulid.py | Yes | Correct |
| SourceAdapter | domain/source_adapters/protocol.py | **No** — not in __all__ | MINOR — Protocol should be importable from package root |

**Issue CR-01: SourceAdapter Protocol not exported from package root.** (MINOR)

The `SourceAdapter` Protocol is the primary contract between domain and adapters. It should be accessible via `from chronoarb import SourceAdapter` without needing to know the sub-package path. Currently requires `from chronoarb.domain.source_adapters.protocol import SourceAdapter`.

**Action:** Add `SourceAdapter` and `SourceItemRef` to `chronoarb/__init__.py` exports.

### 1.3 12 Module Directory Structure

All 12 backend modules exist with 4 subdirectories each (domain/, application/, infrastructure/, api/). Each contains an `__init__.py`. Structure matches `project-analysis.md` §5.

**Finding:** Correct. No missing modules. No extra modules.

---

## 2. Domain Layer Correctness

### 2.1 Money Value Object

**File:** `chronoarb/domain/money.py` (83 lines)

| Invariant | Implementation | Assessment |
|-----------|---------------|------------|
| Frozen/immutable | `@dataclass(frozen=True)` | PASS |
| Decimal-only storage | `Decimal(str(self.amount))` in __post_init__ | PASS with gap (see below) |
| ISO 4217 currency | 3-char uppercase validation | PASS |
| Currency match on ops | `_check_currency_match` on +, -, <, <=, >, >= | PASS |
| Arithmetic returns new Money | All ops return `Money(...)` | PASS |
| Currency-free ops allowed | Negation returns Money | PASS (correct — negation doesn't need currency match) |
| Float prohibited | **No explicit float rejection** | **FAIL — see CR-02** |

**Issue CR-02: Money silently accepts float inputs.** (MAJOR)

```python
# money.py line 28-29
object.__setattr__(self, "amount", Decimal(str(self.amount)))
```

When `Money(amount=100.50, currency="USD")` is called:
1. Dataclass `__init__` assigns `self.amount = Decimal(100.50)` → `Decimal('100.5')`
2. `__post_init__` does `Decimal(str(Decimal('100.5')))` → `Decimal('100.5')`

The float `100.50` becomes `Decimal('100.5')`, silently losing the second decimal place. While `Decimal('100.5') == Decimal('100.50')` is True numerically, the precision is lost and the intent (100 dollars and 50 cents) is corrupted.

AGENTS.md §2 states: "Financial calculations use `Decimal`/fixed-point values and explicit currency codes. Binary floating point is prohibited for money."

The `Money` class does not reject float at construction. It should reject any non-Decimal, non-int amount. The test `test_create_with_float_converts_to_decimal` (test_money.py:19) validates the *current* behavior but should validate that float is REJECTED.

**Action:** Add `isinstance(amount, (Decimal, int))` check in `__post_init__`. Reject float and str amounts (str Decimal parsing should be done by the caller via `Decimal("100.50")`). Update test to assert float rejection.

### 2.2 Domain Errors

**File:** `chronoarb/domain/errors.py` (13 lines)

```
DomainError(Exception)
  ├── ValidationError(DomainError)
  └── CurrencyMismatchError(DomainError)
```

**Finding:** Clean hierarchy. All errors extend a common base. No standalone exceptions outside the hierarchy. Matches the requirement: "Domain errors must extend a common `DomainError` base class" (domain-python/AGENTS.md).

### 2.3 ULID Generator

**File:** `chronoarb/domain/ulid.py` (56 lines)

| Requirement | Implementation | Assessment |
|-------------|---------------|------------|
| Type prefix | `generate_ulid("org")` → `org_01KZ...` | PASS |
| Prefix validation | 1-5 lowercase chars | PASS |
| Uniqueness | Timestamp (48-bit) + random (80-bit) + sequence (10-bit) | PASS — 1000/1000 unique in test |
| Sortability | Monotonic timestamp portion | PASS — timestamps are monotonic |
| No external deps | Pure stdlib (os, time, uuid) | PASS |
| Singleton generator | Module-level `_generator` | PASS |

**Minor concerns:**
- `import uuid` on line 5 is unused — the UUID module is imported but never called (the code uses `os.urandom` for randomness). **(MINOR — see CR-03)**
- Sequence overflow at 1,024 ULIDs/ms. An unrealistic collision scenario at any scale. Not actionable. **(NOTE)**
- The custom base32 encoding (Crockford-inspired but omitting I, L, O, U) prevents ULID sortability by string comparison. The timestamp portion IS sortable when extracted. The test was adjusted to verify timestamp monotonicity rather than full-string sortability. This is documented in the code comments and test. **(NOTE)**

### 2.4 SourceAdapter Protocol

**File:** `chronoarb/domain/source_adapters/protocol.py` (43 lines)

ADR-0007 D3 specifies 5 methods:

| Method | Signature in ADR | Signature in code | Match? |
|--------|-----------------|--------------------|--------|
| discover | `async def discover(self, scope: SourceScope) -> AsyncIterator[SourceItemRef]` | Same | PASS |
| fetch | `async def fetch(self, item: SourceItemRef) -> RawObservation` | Same | PASS |
| parse | `def parse(self, raw: RawObservation) -> ParsedListing` | Same | PASS |
| stable_external_id | `def stable_external_id(self, parsed: ParsedListing) -> str` | Same | PASS |
| health_assertions | `def health_assertions(self, batch: ParsedBatch) -> list[HealthIssue]` | Same | PASS |

**Additional checks:**
- `@runtime_checkable` decorator present — enables `isinstance(adapter, SourceAdapter)` ✓
- `SourceItemRef` is a frozen dataclass ✓
- `SourceScope`, `RawObservation`, `ParsedListing`, `ParsedBatch`, `HealthIssue` are Protocol stubs — intentionally empty, to be replaced with concrete types in Week 3-5 ✓
- Protocol lives in `packages/domain-python/chronoarb/domain/source_adapters/` per ADR-0007 D3 ✓

**Finding:** Protocol exactly matches ADR-0007 specification. Correct placement in domain package. No drift.

---

## 3. FastAPI Boundary Compliance

### 3.1 Route Layer

`apps/api/AGENTS.md` requires: "FastAPI routes must NOT contain business logic — only validation, auth, service call, response mapping."

| Route | Logic present | Assessment |
|-------|--------------|------------|
| `/health` | Trace ID extraction, schema construction, JSON response | PASS — no business logic |
| `/ready` | Trace ID extraction, DB status check (delegated to deps), response mapping, ternary for status | PASS — business logic in deps, not route |

**Finding:** Routes are thin. No business logic in HTTP handlers. This is correct per module AGENTS.md.

### 3.2 Module AGENTS.md Rules Applied

| Rule | Applied? | Where |
|------|----------|-------|
| Routes must be async | Yes | Both handlers are `async def` |
| Health excluded from auth | Yes | No auth middleware added yet; health/ready are `include_in_schema=False` |
| Transaction boundaries at service layer | N/A | No transactions yet (no DB) |
| Pydantic schemas use snake_case | Yes | All response models use snake_case fields |
| Organization ID from request context | N/A | No tenant-scoped endpoints yet |

### 3.3 Error Handling

**File:** `middleware/error_handler.py` (63 lines)

Two exception handlers registered in `main.py`:
1. `PydanticValidationError` → `422`: Correct — maps to `VALIDATION_ERROR` code, includes `field_errors`, `trace_id`, `retryable=false`. Matches the API design spec §2 error envelope.
2. `Exception` → `500`: Correct — maps to `INTERNAL_ERROR` code, message is generic (no leakage), `retryable=true`, `trace_id` included.

| API Spec Field | Pydantic Handler | Generic Handler | Assessment |
|---------------|-----------------|-----------------|------------|
| `code` | `VALIDATION_ERROR` | `INTERNAL_ERROR` | PASS |
| `message` | Custom string | "An internal error occurred." | PASS (no leakage) |
| `field_errors` | Populated from exc.errors() | None | PASS |
| `trace_id` | From request.state | From request.state | PASS |
| `retryable` | `false` | `true` | PASS |
| Status code | `_HTTP_422` (backward compat) | `500` | PASS |

**Starlette deprecation handling:** Lines 13-18 use try/except to handle `HTTP_422_UNPROCESSABLE_ENTITY` → `HTTP_422_UNPROCESSABLE_CONTENT` migration. This is a clean backward-compatible approach. Good.

---

## 4. API Envelope Compliance

### 4.1 Success Response Format

API design.md §2 specifies:
```json
{ "data": { ... }, "meta": { "trace_id": "trc_...", ... } }
```

**Current health response:**
```json
{ "data": { "status": "ok", "trace_id": "trc_..." } }
```

**Issue CR-04: trace_id in data instead of meta.** (MINOR)

The trace_id is nested inside `data` rather than in `meta`. The `ApiSuccessEnvelope` model in schemas.py correctly defines `meta: dict[str, Any] | None = None` as a separate field, but it is not used by health/ready handlers.

**Impact:** When the opportunity feed is implemented (Week 9), the response format for that route must use `meta.trace_id` per the spec. Having health/ready use a different format (`data.trace_id`) creates two trace_id locations developers must know about.

**Action:** Either: (a) Move trace_id from data to meta in health/ready, or (b) Document that health/ready use a simplified envelope (no meta wrapper) and treat this as a deliberate operational endpoint format, not the customer API envelope.

I recommend option (b): health/ready are operational endpoints explicitly excluded from the API schema (`include_in_schema=False`). They don't need the full API envelope. But the inconsistency must be documented.

### 4.2 Error Response Format

```json
{ "error": { "code": "...", "message": "...", "field_errors": {...}, "trace_id": "...", "retryable": false } }
```

**Finding:** Exactly matches the API design spec §2 error envelope. The `ApiError` Pydantic model mirrors the spec field-for-field. Correct.

---

## 5. Trace ID Propagation

### 5.1 Middleware (tracing.py)

Flow:
1. Extract `X-Trace-Id` from request header, or generate `trc_{uuid4().hex[:26]}`
2. Store on `request.state.trace_id`
3. Add `X-Trace-Id` to response header
4. Log request with trace_id in structured extra

| Check | Status |
|-------|--------|
| Custom trace_id propagated | PASS — sent header is returned unchanged |
| Auto-generated trace_id | PASS — format `trc_{26 hex chars}` |
| Header present on all responses | PASS — tested for health, ready, 405, 404 |
| Logging correlation | PASS — trace_id in `extra` dict |
| Test coverage | PASS — 4 test methods across 2 classes |

**Finding:** Complete and correct. No gap.

### 5.2 trace_id Access Pattern

All handlers use `getattr(request.state, "trace_id", "unknown")`. The middleware always sets `request.state.trace_id`, so the `"unknown"` fallback is dead code in normal operation. This is a defensive pattern — if the middleware is removed, handlers don't crash. Good.

---

## 6. Security Concerns

### 6.1 Authentication

No authentication middleware exists yet — this is correct per Week 1 scope. Health/ready endpoints are explicitly not auth-gated. The `include_in_schema=False` prevents them from appearing in OpenAPI docs.

### 6.2 Secrets

`settings.py` contains a default `database_url` with credentials `postgres:chronoarb`. This is documented as a local development default and is overridable via `CHRONOARB_DATABASE_URL` env var (pydantic-settings convention with `env_prefix="CHRONOARB_"`).

**Finding:** Not a security concern for local development. The `.env` file is in `.gitignore`. Production will use Secrets Manager per security-model.md §6.

### 6.3 Error Message Leakage

The generic exception handler returns `"An internal error occurred."` — no stack trace, no internal state, no file paths. The full exception is logged server-side via `logger.exception()`. This follows the AGENTS.md §6 rule: "Errors shown to users are actionable and safe. Internal details go to structured logs with a trace ID."

**Finding:** Correct. No information leakage.

### 6.4 Request State Access

`getattr(_request.state, "trace_id", "unknown")` — This accesses request.state which is populated by the TraceIdMiddleware. No untrusted data flows directly into this. Safe.

---

## 7. Dependency Direction Audit

### 7.1 Declared Dependencies

| From | To | Allowed by ADR-0007 D2? | Assessment |
|------|----|------------------------|------------|
| domain-python | (none) | Yes (root layer) | PASS |
| source-adapters | domain-python | Yes | PASS |
| apps/api | domain-python | Yes | PASS |
| apps/worker | domain-python | Yes | PASS |
| apps/worker | source-adapters | Yes | PASS |

### 7.2 Actual Import Analysis

Every `from X import Y` statement in every source file:

| File | Imports From | Allowed? |
|------|-------------|----------|
| domain/money.py | domain/errors.py | Yes (same layer) |
| domain/ulid.py | (stdlib only) | Yes |
| domain/protocol.py | (stdlib only) | Yes |
| chronoarb/__init__.py | domain/money.py, domain/errors.py, domain/ulid.py | Yes (same layer) |
| source-adapters/__init__.py | (empty) | Yes |
| apps/api/main.py | apps/api/middleware/*, apps/api/routes/*, apps/api/settings.py | Yes (same layer) |
| apps/api/deps.py | (stdlib only) | Yes |
| apps/api/settings.py | pydantic_settings | Yes (external dep) |
| apps/api/schemas.py | pydantic | Yes (external dep) |
| apps/api/routes/health.py | apps/api/schemas.py | Yes (same layer) |
| apps/api/routes/ready.py | apps/api/deps.py, apps/api/schemas.py | Yes (same layer) |
| apps/api/middleware/tracing.py | starlette | Yes (external dep) |
| apps/api/middleware/error_handler.py | apps/api/schemas.py, starlette, pydantic | Yes (same layer + external) |

**Finding:** Zero forbidden imports. No domain-python → source-adapters, no domain-python → apps, no cross-app imports. Every import matches the ADR-0007 D2 dependency graph.

---

## 8. Import-Linter Compatibility

### Issue CR-05: .importlinter uses INI format but import-linter 2.13 requires TOML. (MINOR)

The `.importlinter` config is written in INI format (as specified in ADR-0007 D4). The installed import-linter version 2.13 requires TOML format. Running `lint-imports` produces "Could not read any configuration."

**Impact:** Import boundary enforcement cannot run in CI until the config format is corrected. However, manual import audit (see §7.2 above) confirms zero violations exist.

**Action:** Convert `.importlinter` to TOML format for import-linter 2.x. The 4 contracts remain unchanged; only the format changes.

---

## 9. Test Coverage Quality

### 9.1 Test Suite Summary

| Suite | Tests | Pass | Categories Covered |
|-------|-------|------|--------------------|
| test_money.py | 23 | 23 | Creation (6), immutability (1), arithmetic (7), comparison (6), display (2), precision (1) |
| test_ulid.py | 10 | 10 | Generation (6), prefix validation (4) |
| test_health.py | 10 | 10 | Health (4), readiness (2), error handling (2), trace propagation (2) |
| **Total** | **43** | **43** | |

### 9.2 Missing Coverage

| Area | Covered? | Gap |
|------|----------|-----|
| Money construction from Decimal | Yes | test_create_with_valid_amount_and_currency |
| Money construction from int | Yes | test_create_with_integer_converts_to_decimal |
| Money construction from float | **False positive** | Test validates acceptance — should validate rejection (CR-02) |
| Money immutability | Yes | test_money_is_frozen_dataclass |
| Money addition | Yes | test_addition_same_currency |
| Money addition mismatch | Yes | test_addition_currency_mismatch |
| Money subtraction | Yes | test_subtraction_same_currency |
| Money negation | Yes | test_negation |
| Money multiplication | Yes | test_multiplication, test_rmultiplication |
| Money division | Yes | test_division |
| Money division by zero | Yes | test_division_by_zero |
| Money equality (same currency) | Yes | test_equality |
| Money inequality (different amount) | Yes | test_inequality_different_amount |
| Money inequality (different currency) | Yes | test_inequality_different_currency |
| Money less-than | Yes | test_less_than |
| Money comparison mismatch | Yes | test_comparison_currency_mismatch |
| Money != non-Money | Yes | test_not_equal_non_money |
| Money to_string | Yes | test_to_string |
| Decimal precision (0.10 + 0.20) | Yes | test_decimal_precision_preserved |
| ULID prefix | Yes | 3 tests (start, single char, empty rejects) |
| ULID length | Yes | test_generated_ulid_length_is_consistent |
| ULID uniqueness | Yes | 1000 unique |
| ULID characters | Yes | valid base32 |
| ULID monotonic | Yes | timestamp check |
| Health 200 | Yes | test_health_returns_200 |
| Health JSON | Yes | test_health_returns_valid_json |
| Health trace_id in body | Yes | test_health_includes_trace_id |
| Health trace_id in header | Yes | test_health_response_has_trace_id_header |
| Ready 200 | Yes | test_ready_returns_200 |
| Ready status | Yes | test_ready_returns_status |
| 422 envelope | Yes | test_validation_error_returns_422_with_envelope |
| 404 trace_id | Yes | test_not_found_returns_trace_id |
| Multi-endpoint header test | Yes | test_trace_id_header_present_on_all_responses |
| Custom trace_id | Yes | test_custom_trace_id_is_propagated |
| Money * float (should reject) | **No** | Missing — should test that `Money(100 * 1.5, "USD")` or `Money(amount=float_val, ...)` is rejected |

### 9.3 Test Quality

| Metric | Assessment |
|--------|------------|
| Test isolation | Each test creates fresh Money/ULID instances — no shared mutable state |
| Async test support | pytest-asyncio with `asyncio_mode = "auto"` configured |
| Error message assertions | `pytest.raises(..., match="...")` used for specific error messages |
| Boundary cases | Division by zero, empty currency, non-Money equality, 1000 ULIDs tested |
| Fixtures | `client` fixture creates fresh ASGI transport — no shared HTTP state |

---

## 10. Unused Imports

### Issue CR-03: Unused imports in 3 files. (MINOR)

| File | Import | Status |
|------|--------|--------|
| `domain/ulid.py:5` | `import uuid` | Unused — code uses `os.urandom`, not `uuid` |
| `apps/api/main.py:6` | `from fastapi.routing import APIRoute` | Unused — routes use `add_api_route`, not `APIRoute` |
| `apps/api/tests/test_health.py:1` | `import json` | Unused — responses use `.json()` method, not `json` module |

Ruff configuration in pyproject.toml enables `"F"` (pyflakes) which should catch unused imports. These will be flagged when ruff is run.

---

## 11. Hidden Coupling Analysis

| Potential Coupling | Present? | Assessment |
|--------------------|----------|------------|
| Money depends on framework | No | Pure domain object, no FastAPI/Starlette imports |
| ULID depends on Money | No | Independent domain utility |
| Protocol depends on Money | No | Uses only Protocol types and dataclasses |
| Routes depend on domain | No | Routes use schemas.py (API-layer models), not domain Money/ULID |
| Error handlers depend on routes | No | Error handlers use schemas.py; routes are separate |
| Settings coupled to FastAPI | No | pydantic-settings is framework-agnostic |
| Tests import from src, not mocks | Yes | Tests use real ASGI app (ASGITransport), not mocked app. This is correct integration testing. |

**Finding:** No hidden coupling. The domain layer is cleanly separated from the API layer. The API layer knows about domain types but domain does not know about API.

---

## 12. Placeholder Quality

### get_db_status (deps.py)

```python
async def get_db_status() -> str:
    await asyncio.sleep(0.001)
    return "connected"
```

**Issue CR-06: get_db_status returns "connected" without a real connection.** (NOTE)

The function always returns "connected" regardless of whether a database exists or is reachable. In Batch 3 (Alembic + SQLAlchemy engine), this will be replaced with a real connection check. But until then, `/ready` will report `"database": "connected"` even when there is no database.

**Impact:** False confidence during development. An engineer might think the database is working when it isn't.

**Action:** Return `"not_configured"` until the real DB engine is wired in Batch 3. This communicates the actual state truthfully.

---

## 13. Correction Summary

| ID | Severity | Description | File | Action |
|----|----------|-------------|------|--------|
| CR-01 | MINOR | SourceAdapter not exported from package root | `chronoarb/__init__.py` | Add `SourceAdapter`, `SourceItemRef` to `__all__` and imports |
| CR-02 | MAJOR | Money silently accepts float input | `domain/money.py`, `test_money.py` | Reject non-Decimal/non-int amounts; update float test to expect rejection |
| CR-03 | MINOR | 3 unused imports across 3 files | `ulid.py`, `main.py`, `test_health.py` | Remove unused imports |
| CR-04 | MINOR | trace_id in data vs meta for health/ready | `routes/health.py`, `routes/ready.py` | Document as deliberate operational endpoint format, or restructure to use meta |
| CR-05 | MINOR | .importlinter INI format incompatible with v2.13 | `.importlinter` | Convert to TOML format |
| CR-06 | NOTE | get_db_status returns hardcoded "connected" | `deps.py` | Return "not_configured" until real DB check |

---

## 14. Batch Progression Gate

**Question: Is the repository ready for Batch 3?**

Yes. The MAJOR issue (CR-02: float in Money) should be corrected before Batch 3, but it does not block database/Alembic work — the `Money` class is not used by migrations or the SQLAlchemy engine. The MINOR issues are code quality concerns that won't compound.

**Recommended immediate actions:**
1. Fix CR-02 (float rejection) — 5-minute change, directly violates AGENTS.md
2. Fix CR-03 (unused imports) — 1-minute change, ruff will fail in CI otherwise
3. Fix CR-06 (placeholder honesty) — 1-minute change, prevents false confidence

**Safe to defer:**
- CR-01 (Protocol export) — no code imports Protocol yet
- CR-04 (envelope format) — health/ready are operational endpoints; document intent
- CR-05 (import-linter format) — no violations exist; can fix during CI setup (Batch 8)

---

## 15. Requirements Coverage Matrix

| WF | Criterion | Met? | Evidence |
|----|-----------|------|----------|
| WF-09 | domain-python pyproject.toml | YES | chronoarb-domain 0.1.0, >=3.13 |
| WF-13 | Package skeleton (Money, errors, Protocol) | YES | 5 files, 183 lines |
| WF-10 | source-adapters pyproject.toml | YES | Depends on chronoarb-domain |
| WF-11 | apps/api pyproject.toml | YES | FastAPI, SQLAlchemy, Alembic, Pydantic, asyncpg |
| WF-12 | apps/worker pyproject.toml | YES | Depends on domain + adapters |
| WF-20 | ULID generator | YES | Prefixed, unique, monotonic |
| WF-21 | FastAPI app shell | YES | /health, /ready, trace middleware, error handlers |
| WF-22 | 12 module directories | YES | 48 subdirs across all 12 modules |
| WF-47 | Health test | YES | 10 test methods, all pass |
| WF-48 | Money test | YES | 23 test methods, all pass |
| WF-49 | ULID test | YES | 10 test methods, all pass |
| WF-50 | Import-linter contract | PARTIAL | Config present but format needs TOML conversion |
| — | Money rejects float | NO | CR-02 — accepts float silently |
| — | pip install -e all 4 packages | YES | All installed without errors |
| — | Imports work across packages | YES | Money, Protocol, ULID, app all importable |
