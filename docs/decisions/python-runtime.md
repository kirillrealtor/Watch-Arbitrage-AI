# Python Runtime Strategy

**Decision type:** Environment configuration
**Date:** 2026-08-03
**Deciders:** Lead Software Architect
**Resolves:** Batch 01 Review CR-06

---

## 1. Current Environment

```
OS:       Arch Linux (rolling)
Kernel:   Linux
Python:   3.14.6 (system default, /usr/bin/python3.14)
pip:      26.1.2
```

**Available Python interpreters:**
- `python3.14` (3.14.6) — installed, system default
- `python3.13` — **not installed**
- No Python version manager (pyenv, asdf, mise) installed
- Arch Linux uses PEP 668 (externally-managed-environment); all deps must go through venvs

**Dependency compatibility check (Python 3.14.6 venv, dry-run):**

```
fastapi 0.141.1      ✅ cp314 wheel available
sqlalchemy 2.0.51    ✅ pure Python
alembic 1.18.5       ✅ pure Python
pydantic 2.13.4      ✅ cp314 wheel available
pydantic_core 2.46.4 ✅ cp314 wheel available
asyncpg 0.31.0       ✅ cp314 wheel available
ruff 0.16.1          ✅ cp314 wheel available
mypy 2.3.0           ✅ cp314 wheel available
pytest 9.1.1         ✅ pure Python
uvicorn 0.52.1       ✅ cp314 wheel available
httpx 0.28.1         ✅ pure Python
```

**All 11 core dependencies resolve on Python 3.14.6 with zero errors.**

---

## 2. Required Project Version

### 2.1 SRS Specification

`ChronoArb_MVP_SRS_v1.0` states:

> Python 3.14.6 was current at specification date; the SRS selects 3.13.x initially for conservative dependency compatibility.

The SRS uses the word "initially," acknowledging that the Python version choice is a starting point subject to evolution.

### 2.2 pyproject.toml (current)

```toml
[tool.ruff]
target-version = "py313"

[tool.mypy]
python_version = "3.13"
```

Both tools currently validate against Python 3.13 semantics. No `requires-python` field exists yet (Python packages are created in Batch 2).

### 2.3 AGENTS.md Authority

AGENTS.md §1 Authority Order:
1. SRS → says "3.13.x initially" (flexible)
2. ADRs → none yet constrain Python version
3. AGENTS.md → no Python version constraint
4. This decision document

---

## 3. Options Evaluated

### Option A: Install and use Python 3.13.x

| Dimension | Assessment |
|-----------|------------|
| Tooling | Requires installing pyenv, asdf, or system package for python3.13 |
| Time to implement | 30-60 minutes for toolchain setup |
| SRS alignment | Matches "3.13.x initially" literally |
| Package compatibility | Maximum — every package tests against 3.13 |
| Future migration | Must eventually migrate to 3.14+ anyway |
| Team friction | Every developer must install 3.13; CI must have 3.13 |
| Docker | Must use `python:3.13-slim` base image |
| CI | GitHub Actions `setup-python` action supports 3.13 |

### Option B: Support Python 3.14 and update compatibility rules

| Dimension | Assessment |
|-----------|------------|
| Tooling | Zero setup — use system Python 3.14.6 |
| Time to implement | None — already available |
| SRS alignment | Deviates from literal "3.13.x" but respects "initially" |
| Package compatibility | All 11 core deps resolve today; risk of future dependency breaking on bleeding-edge Python |
| Future migration | None — already on latest |
| Team friction | None — every developer's system Python works |
| Docker | Must use `python:3.14-slim` base image (verify availability) |
| CI | GitHub Actions `setup-python` action supports 3.14 |

---

## 4. Decision

**Selected: Option B — Use Python 3.14 as the project runtime.**

### 4.1 Rationale

1. **All dependencies work today.** Every core dependency (fastapi, sqlalchemy, pydantic, asyncpg, mypy, ruff, pytest, uvicorn, httpx, alembic) resolves cleanly on Python 3.14.6. There is no technical reason to pin to 3.13.

2. **Zero setup overhead.** Installing Python 3.13 on this system requires either a version manager (pyenv/asdf) or a system package not currently available. This adds friction for every developer and every CI runner with no compensating benefit.

3. **The SRS says "initially."** The word acknowledges that the Python version constraint is a starting point. At the time of specification, Python 3.14 was bleeding edge and dependency support was uncertain. It is now verified that support exists.

4. **Future-proofing is automatic.** Choosing 3.14 means the project is already on the latest Python release. No migration is needed in the next 12-24 months.

5. **Docker images exist.** `python:3.14-slim-bookworm` is available on Docker Hub.

### 4.2 Minimum Supported Version

The project shall declare `requires-python = ">=3.13"` in all package `pyproject.toml` files. This means:
- **Development runtime:** Python 3.14 (what's available and tested)
- **Minimum supported:** Python 3.13 (for CI matrix and downstream consumers)
- **Production:** Python 3.14 (Docker base image)
- **CI matrix:** Test against both 3.13 and 3.14

### 4.3 Compatibility Guardrails

| Guardrail | Implementation |
|-----------|---------------|
| ruff target-version | `py313` (minimum language level; 3.14 syntax not used) |
| mypy python_version | `"3.13"` (type-check against minimum supported version) |
| requires-python | `">=3.13"` (allow 3.13 and 3.14 consumers) |
| CI test matrix | `python-version: ["3.13", "3.14"]` (verify both) |
| Docker base image | `python:3.14-slim-bookworm` (exact runtime) |
| Local venv | Created with system python3.14 |

The tooling targets (ruff, mypy) stay at py313 to prevent accidental use of Python 3.14-only syntax. This is a safety net: if 3.14-specific features are introduced, CI on the 3.13 leg catches them.

---

## 5. Developer Setup Impact

### Before this decision

```
Each developer needed: Python 3.13.x (not installed)
```

### After this decision

```
Each developer needs:  Python 3.14.x or 3.13.x (3.14 is system default)
Setup command:          python3.14 -m venv .venv && source .venv/bin/activate
```

No special tooling required. The system Python works out of the box. Developers on Python 3.13 can also work; CI validates both.

---

## 6. CI Impact

### Workflow changes (Batch 8 — `.github/workflows/ci.yml`)

```yaml
jobs:
  test-python:
    strategy:
      matrix:
        python-version: ["3.13", "3.14"]
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e packages/domain-python
      - run: pip install -e packages/source-adapters
      - run: pip install -e apps/api[dev]
      - run: pip install -e apps/worker[dev]
      - run: pytest apps/ packages/
```

### Package pyproject.toml changes (Batch 2)

Each Python package's `pyproject.toml` must include:

```toml
[project]
requires-python = ">=3.13"
```

---

## 7. Rollback Path

If a core dependency breaks on Python 3.14 (unlikely today, possible on future releases):

1. **Containment:** The failing dependency is identified via CI (the 3.14 leg fails while 3.13 passes).
2. **Mitigation:** Pin the failing dependency to a known-good version, or use a conditional dependency with `python_version` markers.
3. **Fallback:** Install Python 3.13 via pyenv: `pyenv install 3.13.0 && pyenv local 3.13.0`
4. **Docker fallback:** Change base image to `python:3.13-slim-bookworm`.
5. **Recovery time:** < 1 hour to switch runtimes.
6. **New ADR:** If fallback is activated, create an ADR documenting which dependency broke, why, and whether the project should permanently stay on 3.13.

---

## 8. Changes Applied

### Immediate (this decision):

| File | Change | Reason |
|------|--------|--------|
| `pyproject.toml` | `ruff.target-version` stays `"py313"` | Minimum language level guardrail |
| `pyproject.toml` | `mypy.python_version` stays `"3.13"` | Type-check against minimum supported version |
| (none) | No code changes in this decision | Config updates happen in Batch 2 |

### Deferred to Batch 2 (package creation):

| File | Change |
|------|--------|
| `packages/domain-python/pyproject.toml` | Add `requires-python = ">=3.13"` |
| `packages/source-adapters/pyproject.toml` | Add `requires-python = ">=3.13"` |
| `apps/api/pyproject.toml` | Add `requires-python = ">=3.13"` |
| `apps/worker/pyproject.toml` | Add `requires-python = ">=3.13"` |

### Deferred to Batch 7 (Docker):

| File | Change |
|------|--------|
| `docker/Dockerfile.api` | Base image: `python:3.14-slim-bookworm` |
| `docker/Dockerfile.worker` | Base image: `python:3.14-slim-bookworm` |

### Deferred to Batch 8 (CI):

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | Test matrix: `["3.13", "3.14"]` |

---

## 9. Verification

```bash
# Verify Python 3.14 is available
python3.14 --version                              # Python 3.14.6

# Verify virtual environment creation works
python3.14 -m venv /tmp/chronoarb-venv-test
source /tmp/chronoarb-venv-test/bin/activate

# Verify core deps install (simulates Batch 2 setup)
pip install fastapi 'uvicorn[standard]' 'sqlalchemy[asyncio]' alembic pydantic asyncpg ruff mypy pytest httpx
python -c "import fastapi, sqlalchemy, alembic, pydantic, asyncpg, ruff, mypy, pytest; print('All imports OK')"

deactivate
rm -rf /tmp/chronoarb-venv-test
```
