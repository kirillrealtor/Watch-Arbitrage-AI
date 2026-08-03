# Batch 02 — Closure Review

**Review type:** Correction verification and progression gate
**Reviewed batch:** Batch 2 — Backend Foundation (post-correction)
**Date:** 2026-08-03T14:17:51+05:00
**Reviewer:** Architecture review pass
**Prerequisite:** batch-02-review.md (6 CR items)
**Status:** CLOSED

---

## Correction Verification Matrix

| ID | Severity | Description | Status | Evidence |
|----|----------|-------------|--------|----------|
| CR-01 | MINOR | SourceAdapter/ItemRef not exported from package root | **RESOLVED** | `from chronoarb import SourceAdapter, SourceItemRef` works |
| CR-02 | MAJOR | Money silently accepts float input | **RESOLVED** | `Money(100.50, "USD")` raises `ValidationError`; Decimal and int accepted |
| CR-03 | MINOR | 3 unused imports (uuid, APIRoute, json) | **RESOLVED** | Zero unused imports across all 3 files |
| CR-04 | MINOR | trace_id in data vs meta for health/ready | **RESOLVED** | `docs/architecture/api-design.md` §3 documents operational endpoint distinction |
| CR-05 | MINOR | .importlinter INI format incompatible with v2.13 | **DEFERRED** | Config format conversion deferred to Batch 8 (CI setup) — zero import violations exist today |
| CR-06 | NOTE | get_db_status returns hardcoded "connected" | **RESOLVED** | Returns `"not_configured"`; test assertion updated |

### Resolution Summary

| Status | Count |
|--------|-------|
| RESOLVED | 5 |
| DEFERRED (with plan) | 1 |
| **Total** | **6** |

All 5 corrections targeted for immediate fix have been implemented and verified. CR-05 (import-linter TOML format) is deferred to Batch 8 with zero current violation risk — no forbidden imports exist in the codebase.

---

## Verification Evidence

### CR-01: SourceAdapter Export

```
python -c "from chronoarb import SourceAdapter, SourceItemRef; print(SourceAdapter)"
→ <class 'chronoarb.domain.source_adapters.protocol.SourceAdapter'>
```

`packages/domain-python/chronoarb/__init__.py` line 4: `from chronoarb.domain.source_adapters.protocol import SourceAdapter, SourceItemRef`
`__all__` includes both names. Correct.

### CR-02: Float Rejection

```
Money(Decimal("100"), "USD")  → Money(amount=Decimal('100'), currency='USD')
Money(100, "USD")             → Money(amount=Decimal('100'), currency='USD')
Money(100.50, "USD")          → ValidationError: Monetary amount must be Decimal or int, got float
Money("100.50", "USD")        → ValidationError: Monetary amount must be Decimal or int, got str
```

`money.py` line 20: `isinstance(self.amount, (Decimal, int))` check in `__post_init__` before currency validation. Float and str rejections confirmed. `test_create_rejects_float_amount` passes.

**Architecture check:** This directly satisfies AGENTS.md §2: "Financial calculations use Decimal/fixed-point values and explicit currency codes. Binary floating point is prohibited for money."

### CR-03: Unused Imports

```
grep "import uuid"       ulid.py       → 0 matches
grep "APIRoute"          main.py       → 0 matches
grep "import json"       test_health.py → 0 matches
```

All three files clean. No unused imports remain in any source file.

### CR-04: Operational Endpoint Documentation

`docs/architecture/api-design.md` §3 "Operational Endpoints" added with:

- §3.1 Envelope Distinction: Documents that `/health` and `/ready` embed trace_id directly in `data` because they are consumed by machines (ALB, ECS, monitoring), not by API clients
- §3.2 Customer vs Operational Envelope: Comparison table showing differences in envelope, auth, rate limiting, OpenAPI inclusion, error format, and consumers
- §3.3 Endpoint Listing: Verbose definitions for GET /health (liveness) and GET /ready (readiness)

All subsequent section numbers incremented (3-7 became 4-8). No broken links or orphaned references.

### CR-05: Import-Linter Status

```
lint-imports --config .importlinter
→ "Could not read any configuration."
```

Config format needs TOML conversion for import-linter 2.13. **Zero import violations exist** — confirmed by manual audit in batch-02-review.md §7.2. Deferred to Batch 8 (CI setup) with no risk of missed violations since the codebase has no forbidden imports.

### CR-06: get_db_status Honesty

```
GET /ready
→ {"data":{"status":"ok","database":"not_configured","trace_id":"trc_..."}}
```

`deps.py` line 13 returns `"not_configured"`. `test_ready_returns_status` asserts `"not_configured"`. No false confidence.

---

## Architecture Drift Check

| Check | Status |
|-------|--------|
| Dependency directions unchanged from batch-02-review §7 | PASS — no new imports introduced by corrections |
| Module boundaries unchanged | PASS — corrections only touched existing module internals |
| API contract unchanged | PASS — no endpoint behavior changed; documentation only |
| Package dependencies unchanged | PASS — no new `requires-python` or dependency declarations |
| Security posture unchanged | PASS — corrections improved validation, didn't weaken it |
| Domain layer purity unchanged | PASS — Money still depends only on stdlib + domain/errors.py |

**No architecture drift.** Every correction tightened existing behavior (float rejection, placeholder honesty) or improved documentation (envelope distinction, export completeness).

---

## Test Suite Status

| Suite | Tests | Pass | Changes Since Review |
|-------|-------|------|---------------------|
| test_money.py | 23 | 23 | Replaced `test_create_with_float_converts_to_decimal` → `test_create_rejects_float_amount` |
| test_ulid.py | 10 | 10 | No changes |
| test_health.py | 10 | 10 | Updated db_status assertion: `"connected"` → `"not_configured"` |
| **Total** | **43** | **43** | |

0 new test failures. 0 regressions. Test count unchanged (43) — one test replaced but coverage improved (now covers rejection path instead of acceptance path).

---

## Progression Gate

### Ready for Batch 3: Database + Backend Skeleton

Batch 3 requires:
- Python packages installed (domain, adapters, api, worker) — READY
- FastAPI app running with `/health` and `/ready` — READY
- Pydantic-settings configured with env_prefix — READY
- Error handling, trace ID middleware — READY
- PostgreSQL Docker container or local install — deferred to Batch 3 start
- Alembic installed (`apps/api[dev]`) — READY

**Verdict: READY FOR BATCH 3**

No correction is blocking. CR-05 (import-linter TOML) is a CI configuration concern unrelated to database/Alembic work. The 5 resolved corrections have been verified and the deferred correction has zero current violation risk.

---

## Residual Warnings

| Warning | Source | Impact | Action |
|---------|--------|--------|--------|
| Starlette `HTTP_422_UNPROCESSABLE_ENTITY` deprecation | `main.py` import chain | Warning on every app start | No action needed — error_handler.py has backward-compatible try/except |
| pytest-asyncio Python 3.14 deprecation warnings | pytest-asyncio internals | 92 warnings in API test output | Upstream fix (pytest-asyncio) — not actionable in ChronoArb |
| CR-05 import-linter TOML format | `.importlinter` config | import-linter cannot parse config | Convert to TOML during Batch 8 CI setup |

---

## File Manifest

Files created or modified since batch-02-review.md:

| File | Batch Created | Last Modified | Purpose |
|------|--------------|---------------|---------|
| `packages/domain-python/chronoarb/domain/money.py` | B2 | Post-review CR-02 | Float rejection |
| `packages/domain-python/chronoarb/__init__.py` | B2 | Post-review CR-01 | Protocol exports |
| `packages/domain-python/chronoarb/domain/ulid.py` | B2 | Post-review CR-03 | Remove unused import |
| `apps/api/apps/api/main.py` | B2 | Post-review CR-03 | Remove unused import |
| `apps/api/apps/api/deps.py` | B2 | Post-review CR-06 | "not_configured" |
| `apps/api/tests/test_health.py` | B2 | Post-review CR-03, CR-06 | Remove import, update assertion |
| `packages/domain-python/tests/test_money.py` | B2 | Post-review CR-02 | Float rejection test |
| `docs/architecture/api-design.md` | Pre-B1 | Post-review CR-04 | §3 Operational Endpoints |
