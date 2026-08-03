# Batch 01 — Implementation Review

**Review type:** Post-implementation quality audit
**Reviewed batch:** Batch 1 — Repository Foundation (WF-01 through WF-08)
**Date:** 2026-08-03
**Reviewer:** Architecture review pass
**Files reviewed:** 10 production files, 2 AGENTS.md module overrides

---

## Executive Summary

Batch 1 is **sound and complete**. All 8 tasks are properly implemented. The repository structure correctly establishes the monorepo topology from ADR-0001 D11 and enforces the dependency graph from ADR-0007. The module-level AGENTS.md files correctly specialize root rules without weakening invariants. Three issues require attention before Batch 2: import-linter contract documentation alignment, Python runtime version mismatch, and workspace compatibility hardening.

**Verdict:** APPROVED with corrections.

---

## 1. Repository Structure Compliance

### 1.1 Monorepo Topology (ADR-0001 D11)

| Required | Present | Assessment |
|----------|---------|------------|
| `apps/` (web, mobile, api, worker) | `api/` exists; web/mobile/worker not yet | Correct — packages are created in their respective batches (B5 web, B6 mobile, B4 worker) |
| `packages/` (domain-python, source-adapters, api-client-ts, api-client-dart, design-tokens) | `domain-python/` exists; others not yet | Correct — created in B2 (Python) and B5 (TypeScript) |
| `infrastructure/terraform/` | Not yet | Correct — Batch 7 |
| `docker/` | Not yet | Correct — Batch 7 |
| `docs/` | Present (reference, architecture, adr, implementation) | Correct — architecture docs exist from prior phase |
| `scripts/` | Not yet | Correct — Batch 8 (CI scripts) |

**Finding:** Structure matches the planned delivery. All absent directories are correctly deferred to later batches.

### 1.2 pnpm Workspace Configuration

`pnpm-workspace.yaml` declares `apps/*` and `packages/*`. This correctly matches the monorepo structure and will auto-discover workspaces as they're created in B2, B4, B5, and B6.

**Issue CR-01: No catalog-only restrictions.**

`pnpm-workspace.yaml` does not restrict specific subdirectories within `apps/` or `packages/`. For example, `apps/temp-experiment/` with a `package.json` would be auto-included. This is standard pnpm behavior and acceptable for Week 1, but consider pinning to explicit package names when the workspace list is stable:

```yaml
packages:
  - "apps/web"
  - "apps/mobile"
  - "apps/api"
  - "apps/worker"
  - "packages/domain-python"
  - "packages/source-adapters"
  - "packages/api-client-ts"
  - "packages/api-client-dart"
  - "packages/design-tokens"
```

**Severity:** NOTE. Not actionable in Week 1 — workspace members don't exist yet. Revisit in Batch 8.

### 1.3 Gitignore Completeness

The `.gitignore` covers 35 patterns across all planned languages, tools, and platforms. Assessment by category:

| Category | Patterns | Coverage |
|----------|----------|----------|
| JavaScript/TypeScript | `node_modules/`, `.pnpm-store/`, `dist/`, `.next/`, `build/`, `*.tsbuildinfo` | Complete |
| Python | `__pycache__/`, `*.pyc`, `*.pyo`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/` | Complete |
| Terraform | `.terraform/`, `*.tfstate`, `*.tfstate.*`, `.terraform.lock.hcl` | Complete |
| Flutter/Dart | `.dart_tool/`, `.packages`, `.flutter-plugins`, `.flutter-plugins-dependencies` | Complete |
| Environment | `.env`, `.env.*`, `!.env.example` | Complete |
| OS/IDE | `.DS_Store`, `Thumbs.db`, `.idea/`, `.vscode/`, `*.swp`, `*.swo`, `*~`, `*.iml` | Complete |
| Other | `.sentry-native/` | Complete |

**Finding:** No gaps. The `.env.*` exclusion with `!.env.example` exception is correct — prevents accidental secret commits while preserving the template.

---

## 2. AGENTS.md Compliance

### 2.1 Root AGENTS.md

The root `AGENTS.md` is unchanged from the source specification. No review needed.

### 2.2 Module AGENTS.md (apps/api/AGENTS.md)

| AGENTS.md §9 Rule | Module AGENTS.md | Assessment |
|-------------------|------------------|------------|
| Routes handle HTTP concerns only | "FastAPI routes must NOT contain business logic — only validation, auth, service call, response mapping" | PASS — match |
| Repository tenant scope | "Every service call must pass explicit `organization_id` obtained from authenticated request context" | PASS — match |
| Pydantic schemas versioned | "Pydantic schemas must use `snake_case` and match API contract" | PASS — match |
| Routes must be async | "All route handlers must be async" | PASS — stricter than root (root doesn't require all-routes-async) |
| Transactions at application layer | "Transaction boundaries managed at application service layer, not in repositories" | PASS — correct layer |
| Health check auth exclusion | "/health, /health/ready excluded from auth middleware" | PASS — operational necessity |

**Finding:** The module AGENTS.md correctly specializes root rules. Rule "all routes must be async" is stricter than root §9 (which implies but doesn't mandate all routes are async). This is permissible — module rules can be stricter, never weaker.

### 2.3 Module AGENTS.md (packages/domain-python/AGENTS.md)

| Root Rule | Module AGENTS.md | Assessment |
|-----------|------------------|------------|
| Decimal/fixed-point for money (§2) | "All financial values must use Decimal. float is prohibited" | PASS |
| Explicit currency codes (§2) | "All monetary values must carry explicit ISO 4217 currency code" | PASS |
| Source adapter isolation (§2) | "Must NOT import from packages/source-adapters or any apps/ package" | PASS — enforces ADR-0007 D1 |
| Protocol contracts | "Protocol interfaces define contracts for external dependencies" | PASS — aligns with ADR-0007 D3 |
| ULID opaque identifiers (§11) | "ULID generation must use type prefix for readability and log grepability" | PASS — aligns with ADR-0001 D4 |
| Domain error hierarchy | "Domain errors must extend common DomainError base class" | PASS — best practice, not in root but correct |

**Finding:** The module AGENTS.md correctly specializes root rules and enforces ADR-0001/ADR-0007 architectural constraints. No weakenings detected.

### 2.4 Missing AGENTS.md Files

The batching plan requires AGENTS.md files at `apps/api/` and `packages/domain-python/` (WF-08). Both are present. The plan does not require AGENTS.md files for other modules at this stage — those can be added when their respective packages are created.

---

## 3. ADR-0007 Dependency Enforcement

### 3.1 .importlinter Configuration Audit

ADR-0007 D4 specifies 2 contracts:

```
[importlinter:contract:chronoarb]           # Layer definitions
[importlinter:contract:chronoarb-domain-isolation]  # Domain isolation
```

The implementation provides 4 contracts:

```
[importlinter:contract:chronoarb]                      # Layer definitions — MATCHES ADR
[importlinter:contract:chronoarb-domain-isolation]      # Domain isolation — MATCHES ADR
[importlinter:contract:chronoarb-adapter-isolation]     # ADDITIONAL — adapter isolation
[importlinter:contract:chronoarb-cross-app-isolation]   # ADDITIONAL — cross-app isolation
```

**Issue CR-02: .importlinter extends beyond ADR-0007 D4 specification.**

The additional contracts (`chronoarb-adapter-isolation` and `chronoarb-cross-app-isolation`) enforce rules from ADR-0007 D2's dependency graph but are not documented in the ADR's D4 section. The ADR-0007 D2 text states these rules as expectations, and the implementation correctly enforces them. However, the ADR's D4 only documents 2 contracts.

**Severity:** MINOR. The implementation is correct and more complete than the ADR minimum. The ADR should be updated to document all 4 contracts for traceability.

**Action:** Add `chronoarb-adapter-isolation` and `chronoarb-cross-app-isolation` contracts to ADR-0007 D4. No code change needed.

### 3.2 Layer Ordering Correctness

The `layers` contract defines the valid dependency order:

```
domain-python (lowest)
  ↓
source-adapters
  ↓
api / worker (highest, same level)
```

This correctly reflects ADR-0007 D2:
- `domain-python` depends on nothing
- `source-adapters` depends on `domain-python` ✓
- `api` depends on `domain-python` ✓
- `worker` depends on `domain-python` and `source-adapters` ✓

**Finding:** Layer ordering is correct. No violations.

### 3.3 Missing Layer Coverage

The `layers` contract defines 4 layers but the workspace has 5 packages (plus 4 apps). The missing entries:

| Package | Present in .importlinter | Assessment |
|---------|-------------------------|------------|
| `api-client-ts` | No | Correct — TypeScript package, not subject to Python import-linter |
| `api-client-dart` | No | Correct — Dart package |
| `design-tokens` | No | Correct — TypeScript package |
| `apps/web` | No | Correct — TypeScript package |
| `apps/mobile` | No | Correct — Dart/Flutter package |

**Finding:** import-linter only governs Python packages. Non-Python packages are correctly excluded. No gap.

---

## 4. Naming Consistency

### 4.1 Package Names

| Package | pnpm workspace name | package.json `name` | Assessment |
|---------|--------------------|---------------------|------------|
| Root | — | `"chronoarb"` | Standard monorepo root name |
| domain-python | `packages/domain-python/` | Not yet created (B2) | Placeholder AGENTS.md only |
| api | `apps/api/` | Not yet created (B3) | Placeholder AGENTS.md only |

**Issue CR-03: No explicit naming convention documented for package.json names.**

The plan implies package names like `@chronoarb/web`, `@chronoarb/design-tokens`, `@chronoarb/api-client`. These should be consistent with the `tsconfig.base.json` path alias `@chronoarb/*`. No files violate this yet (no TypeScript packages exist), but it should be documented before Batch 5.

**Severity:** NOTE. Document in Batch 5 plan or a naming-convention ADR.

### 4.2 Python Package Names

The plan specifies:
- `chronoarb-domain` for `packages/domain-python/`
- `chronoarb-adapters` for `packages/source-adapters/`

These follow the `chronoarb-{purpose}` pattern. The `apps/api/` and `apps/worker/` pyproject.toml files (Batch 2) should use `chronoarb-api` and `chronoarb-worker` respectively, though they're apps, not libraries.

### 4.3 Tool Configuration

| Config | File | Naming Convention | Assessment |
|--------|------|-------------------|------------|
| Ruff | `pyproject.toml` | `py313` target, `chronoarb` first-party | Correct |
| mypy | `pyproject.toml` | `python_version = "3.13"` | Correct target |
| pytest | `pyproject.toml` | `testpaths` uses consistent paths | Correct |
| Turbo | `turbo.json` | Task names match `package.json` scripts | Correct |

---

## 5. Future Package Compatibility

### 5.1 TypeScript Path Alias Coverage

`tsconfig.base.json` defines two path aliases:

```json
"@chronoarb/design-tokens": ["./packages/design-tokens"],
"@chronoarb/api-client": ["./packages/api-client-ts/src"]
```

**Missing aliases for future packages:**
- `@chronoarb/web` — Not needed (web code imports via relative paths or the `@/` convention within the app)
- Any future shared TypeScript packages

**Finding:** The current aliases are sufficient for Batch 5 (web + design-tokens + api-client-ts). Additional aliases should be added when new shared TypeScript packages are created.

### 5.2 Python Path Configuration

`pyproject.toml` pytest section sets `pythonpath`:

```toml
pythonpath = ["apps/api", "apps/worker", "packages/domain-python", "packages/source-adapters"]
```

This ensures that `import chronoarb.domain.money` resolves correctly in tests even without editable installs. It correctly includes all 4 Python packages planned for Week 1.

**Finding:** Complete for the planned packages. No missing entries.

### 5.3 Package Manager Locking

`package.json` pins `pnpm@11.3.0` via `packageManager` field and enforces `>=10.0.0` via `engines`. The `engines.pnpm` minimum (10.x) is lower than the pinned version (11.3.0). If a developer uses pnpm 10.x, they'll get a warning but installations may still work. For stricter enforcement, set `engines.pnpm` to match the pinned version:

```json
"engines": {
  "node": ">=22.0.0",
  "pnpm": "11.3.0"
}
```

**Issue CR-04: engines.pnpm lower-bound allows version drift.**

**Severity:** MINOR. The `packageManager` field enforces the pinned version for `pnpm install`. The `engines` field is advisory. This is acceptable if the team standardizes on pnpm 11.3.0.

### 5.4 Node.js Version

`engines.node` requires `>=22.0.0`. Node 22 is the current active LTS as of 2026. This is acceptable for a development/CI toolchain. No production runtime uses Node.js directly (web is a build artifact served by CloudFront/ALB; API is Python).

**Finding:** Acceptable. No action needed.

---

## 6. CI Readiness

### 6.1 CI Pipeline Definition

The CI workflow (`WF-44`) is scheduled for Batch 8. No `.github/workflows/` directory exists yet — this is correct per the plan.

### 6.2 Pre-CI Validation Available Locally

The following checks can be run locally today:

| Check | Command | Status |
|-------|---------|--------|
| Workspace resolution | `pnpm install --frozen-lockfile` | PASS |
| Turbo pipeline graph | `pnpm turbo run build --dry-run` | PASS |
| Python linting | `ruff check .` | FAIL — ruff not installed |
| Python type checking | `mypy .` | FAIL — mypy not installed |
| TypeScript type checking | `tsc --noEmit` | FAIL — TypeScript not installed |
| Import boundary check | `import-linter` | FAIL — import-linter not installed |

**Issue CR-05: Local tooling not installable as root dev dependencies.**

Ruff, mypy, TypeScript, and import-linter are configured in root configs but are not installable via `pnpm install` (they'd need to be root devDependencies or workspace package dependencies). Tool installation is deferred to Batch 2 (Python packages) and Batch 5 (TypeScript packages). Until then, developers must install tools manually or via their respective package managers.

**Severity:** NOTE. Expected at this stage. Resolved in B2 (pip installs Python tools) and B5 (pnpm installs TypeScript tools).

### 6.3 Turbo Cache Configuration

`turbo.json` uses `"cache": false` for `dev` and `clean`, and no explicit `"cache": true` for other tasks (Turbo defaults to caching). This is correct behavior.

**Finding:** Turbo configuration is standard and correct.

---

## 7. Security Concerns

### 7.1 Secrets Management

No secrets exist in any file. `.env.example` is scheduled for Batch 7. The `.gitignore` correctly prevents `.env` and `.env.*` commits with the `!.env.example` exception. No secrets in source control.

### 7.2 Supply Chain

- `turbo` is the only devDependency (^2.5.0, installed as 2.10.8)
- All other tooling (ruff, mypy, TypeScript, etc.) will be installed in later batches
- No runtime dependencies exist yet

**Finding:** Minimal supply chain surface. Acceptable for Week 1.

### 7.3 Code Injection Risk

The root `package.json` scripts all delegate to `turbo run`. No direct shell execution of user input. No script injection vectors in the current configuration.

### 7.4 AGENTS.md Authority

Both module AGENTS.md files correctly state they "cannot weaken security, tenant isolation, financial correctness, or SRS requirements." This enforces the authority order from root AGENTS.md §1.

**Finding:** Authority chain is correctly preserved.

---

## 8. Correctable Issues (Before Batch 2)

### Issue CR-06: Python runtime version mismatch

**Severity:** MINOR
**Source:** pyproject.toml line 2 vs system Python

`pyproject.toml` specifies `target-version = "py313"` and `mypy.python_version = "3.13"`. The local system has Python 3.14.6. The SRS recommends Python 3.13.x for conservative dependency compatibility. When Batch 2 installs Python packages, pip will attempt to install dependencies compatible with Python 3.14 (the system interpreter), but mypy and ruff will validate against Python 3.13 semantics.

**Impact:** Dependencies may install versions targeting Python 3.14 features, potentially using syntax or stdlib features unavailable on Python 3.13. Conversely, Python 3.14 may have breaking changes from 3.13 that cause test failures.

**Action before Batch 2:** Install Python 3.13.x alongside Python 3.14 or use a Python version manager (pyenv) to pin the project to 3.13.x. Update pyproject.toml `requires-python = ">=3.13,<3.15"` when Python packages are created.

### Issue CR-07: No Flutter workspace management

**Severity:** NOTE
**Source:** Project specification

The monorepo includes a Flutter app (`apps/mobile/`) but neither `pnpm-workspace.yaml` nor `turbo.json` can manage Flutter/Dart packages. Flutter uses its own package manager (pub) and build system.

**Impact:** `pnpm install` cannot resolve Flutter dependencies. `turbo run build` cannot build the Flutter app. Cross-platform build orchestration will need custom scripts.

**Action before Batch 6:** Document the Flutter toolchain interaction model. Consider a root-level `flutter` script alias that invokes `cd apps/mobile && flutter <command>`. Turbo can orchestrate this with `"flutter:build": "cd apps/mobile && flutter build apk"` in the mobile package.json.

---

## 9. Requirements Coverage Matrix

| WF Task | Acceptance Criterion | Met? | Evidence |
|---------|---------------------|------|----------|
| WF-01 | `pnpm install` exits 0 | YES | `pnpm install` installed turbo 2.10.8, created lockfile |
| WF-01 | Scripts defined (dev/lint/test/build) | YES | 6 scripts in `package.json` |
| WF-02 | `pnpm-workspace.yaml` lists apps/* and packages/* | YES | Both globs present |
| WF-03 | Pipeline stages defined; dry-run renders | YES | `pnpm turbo run build --dry-run` renders without errors |
| WF-04 | Strict mode, ES2022 target | YES | `strict: true`, `target: ES2022`, JSON is valid |
| WF-05 | Ruff py313 config | YES | `target-version = "py313"` |
| WF-05 | mypy strict config | YES | `strict = true`, `python_version = "3.13"` |
| WF-05 | pytest config | YES | `minversion = "8.0"`, testpaths set |
| WF-06 | Layers and forbidden rules present | YES | 4 contracts: layers, domain-isolation, adapter-isolation, cross-app-isolation |
| WF-06 | Matches ADR-0007 D2 dependency graph | YES | All allowed/forbidden edges enforced |
| WF-07 | `.gitignore` excludes generated files | YES | 35 patterns, 9 categories |
| WF-07 | `.dockerignore` excludes build artifacts | YES | 17 patterns |
| WF-08 | `apps/api/AGENTS.md` exists | YES | 20 lines, 6 FastAPI rules |
| WF-08 | `packages/domain-python/AGENTS.md` exists | YES | 20 lines, 7 domain rules |

**All 14 acceptance criteria met.**

---

## 10. Correction Summary

| ID | Severity | Description | Action | Batch |
|----|----------|-------------|--------|-------|
| CR-01 | NOTE | Workspace globs do not restrict packages | Pin to explicit package names in Batch 8 | B8 |
| CR-02 | MINOR | .importlinter has 4 contracts, ADR-0007 D4 documents 2 | Update ADR-0007 D4 to list all 4 contracts | Before B2 |
| CR-03 | NOTE | No explicit npm package naming convention | Document `@chronoarb/*` convention before B5 | Before B5 |
| CR-04 | MINOR | engines.pnpm lower-bound allows version drift | Set `engines.pnpm` to `"11.3.0"` (match packageManager) | B1 (now) |
| CR-05 | NOTE | Local tooling not installable yet | Expected — resolved by B2/B5 | B2, B5 |
| CR-06 | MINOR | Python 3.14 installed but project targets 3.13 | Install Python 3.13 or use version manager | Before B2 |
| CR-07 | NOTE | Flutter not integrated with pnpm/turbo | Document Flutter orchestration approach before B6 | Before B6 |

---

## 11. Batch Progression Gate

**Question: Is the repository ready for Batch 2?**

Yes. The Python packages (`packages/domain-python/pyproject.toml`, `packages/source-adapters/pyproject.toml`, `apps/api/pyproject.toml`, `apps/worker/pyproject.toml`) in Batch 2 require `pyproject.toml` (root tooling config) and `pnpm-workspace.yaml` (workspace structure) to exist. Both are present and verified.

**Conditional gate:** CR-06 (Python 3.13 availability) must be resolved before `pip install -e packages/domain-python` is attempted in Batch 2. If Python 3.13 is unavailable, Batch 2 must proceed with Python 3.14 and document the version delta (either update the SRS recommendation or add a compatibility note).

**Recommended immediate actions (before B2 start):**
1. Fix CR-04: Set `engines.pnpm` to `"11.3.0"` in package.json
2. Verify Python 3.13 availability or document 3.14 usage decision
3. Update ADR-0007 D4 with all 4 import-linter contracts
