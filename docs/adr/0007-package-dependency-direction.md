# ADR-0007: Package Dependency Direction

**Status:** Accepted
**Date:** 2026-08-03
**Deciders:** Lead Software Architect
**Supersedes:** ADR-0001 §4.1 (dependency rules)
**Resolves:** Architecture Review MAJOR-04

---

## Context

ADR-0001 D11 defines the monorepo structure with four `apps/` and five `packages/`. The dependency rules in `project-analysis.md` §4.1 define the allowed import directions between these packages. However, the current rules are incomplete:

1. `packages/source-adapters` must import `packages/domain-python` (to implement the `SourceAdapter` Protocol and use domain types), but this dependency is not declared.
2. The dependency listing omits `api-client-ts` and `api-client-dart` from the explicit rules despite them being in the monorepo tree.

Additionally, ADR-0001 D9 mandates source adapter isolation, and ADR-0002 D2 adds `organization_id` to `alert_deliveries`. These decisions must be reflected in the dependency graph.

---

## Problem

### P1: source-adapters → domain-python dependency is undeclared

The `SourceAdapter` Protocol interface, domain value objects (e.g., `Money`, `Currency`), and core types (e.g., `ListingPrice`, `NormalizedListing`) live in `packages/domain-python`. Source adapters must import these to function:

```python
# packages/source-adapters/ebay/adapter.py
from chronoarb.domain.source_adapters import SourceAdapter, SourceItemRef, RawObservation
from chronoarb.domain.money import Money, Currency
```

Without this declared dependency, developers could accidentally bypass it at review, and CI import-linter checks would not enforce the relationship.

### P2: Dependency rules don't list all packages

The dependency rules in `project-analysis.md` §4.1 reference `api-client-ts` and `api-client-dart` indirectly (through `apps/web` and `apps/mobile` declarations) but the packages themselves are not enumerated in the rules. This makes the rules harder to enforce with tooling.

### P3: domain-python must NOT import from any other package

ADR-0001 D9 states that core modules must not import source-specific code. This is enforced by the existing rule but should be reaffirmed with the new dependency.

---

## Decision

### D1: Declare `packages/source-adapters → packages/domain-python`

Add the following dependency to the graph:

```
packages/source-adapters → packages/domain-python
```

This is a **one-directional** dependency. `packages/domain-python` MUST NOT import from `packages/source-adapters` or any `apps/` package. The reverse dependency is the entire purpose of the adapter isolation pattern: domain defines interfaces, adapters implement them.

### D2: Complete dependency graph

The full, corrected dependency graph:

```
# App → Package dependencies (runtime)
apps/api        → packages/domain-python
apps/worker     → packages/domain-python
apps/worker     → packages/source-adapters
apps/web        → packages/api-client-ts
apps/web        → packages/design-tokens
apps/mobile     → packages/api-client-dart
apps/mobile     → packages/design-tokens

# Package → Package dependencies (compile-time)
packages/source-adapters    → packages/domain-python
packages/api-client-ts      → (none — generated code, no project dependencies)
packages/api-client-dart    → (none — generated code, no project dependencies)
packages/design-tokens      → (none — pure data, no project dependencies)

# Forbidden dependencies (enforced by import-linter in CI)
packages/domain-python  →  packages/source-adapters   (MUST NOT)
packages/domain-python  →  apps/*                     (MUST NOT)
packages/source-adapters → apps/*                     (MUST NOT)
apps/*                   →  apps/*                    (MUST NOT — no cross-app imports)
```

### D3: Source Adapter Protocol location

The `SourceAdapter` Protocol and related types (`SourceItemRef`, `RawObservation`, `ParsedListing`, `HealthIssue`) shall live in `packages/domain-python/chronoarb/domain/source_adapters/`. This directory contains only the abstract interface — no implementation code, no HTTP clients, no source-specific logic.

```python
# packages/domain-python/chronoarb/domain/source_adapters/protocol.py
from typing import Protocol, AsyncIterator, runtime_checkable

@runtime_checkable
class SourceAdapter(Protocol):
    source_key: str
    adapter_version: str
    async def discover(self, scope: SourceScope) -> AsyncIterator[SourceItemRef]: ...
    async def fetch(self, item: SourceItemRef) -> RawObservation: ...
    def parse(self, raw: RawObservation) -> ParsedListing: ...
    def stable_external_id(self, parsed: ParsedListing) -> str: ...
    def health_assertions(self, batch: ParsedBatch) -> list[HealthIssue]: ...
```

### D4: Enforcement via import-linter

CI shall run `import-linter` (Python) with a contract that enforces the complete dependency graph:

```ini
# .importlinter
[importlinter:contract:chronoarb]
name = ChronoArb package boundaries
type = layers

layers =
    domain-python
    source-adapters
    api
    worker

[importlinter:contract:chronoarb-domain-isolation]
name = Domain must not import adapters or apps
type = forbidden
source_modules =
    chronoarb.domain
forbidden_modules =
    chronoarb.adapters
    apps.api
    apps.worker
```

---

## Alternatives Considered

### Alternative A: SourceAdapter Protocol in source-adapters package (rejected)

Put the Protocol definition in `packages/source-adapters/` alongside the implementations.

**Rejected because:**
- Forces `packages/domain-python → packages/source-adapters` dependency (domain depends on adapters), violating ADR-0001 D9.
- Inverts the dependency direction: domain should define what it needs, adapters should fulfill the contract.
- If domain depends on adapters, every change to adapter structure forces domain recompilation.
- The established pattern in hexagonal/clean architecture is: domain defines ports (interfaces), infrastructure implements them.

### Alternative B: Shared interfaces package (rejected)

Create a third package `packages/interfaces/` that both `domain-python` and `source-adapters` depend on.

**Rejected because:**
- Adds a package boundary for a single Protocol definition.
- The Protocol is a domain concern (it defines what the domain needs from external sources).
- A shared interface package is justified when there are many cross-cutting interfaces; for one Protocol, it's over-engineering.
- Can be extracted later via expand/contract if more shared interfaces emerge.

### Alternative C: No explicit dependency declaration (rejected)

Leave the dependency implicit (developers just know to import it) without formalizing it in the dependency rules.

**Rejected because:**
- AGENTS.md §5: "Reuse and duplication rules" and the playbook require explicit, enforceable boundaries.
- Without explicit rules, CI cannot verify them.
- Implicit dependencies lead to architectural erosion over time.

---

## Consequences

### Positive

- Complete, enforceable dependency graph for CI.
- Source adapters can import domain types (Protocol, Money, Currency, etc.) with clear justification.
- Domain package remains pure — no dependency on adapters or applications.
- Generated packages (api-client-ts, api-client-dart, design-tokens) are explicitly documented as having no project dependencies.
- Import-linter can enforce the complete graph in CI, preventing architectural erosion.

### Negative

- import-linter configuration requires maintenance when new packages are added.
- Developers must be aware of the dependency rules (documented in project-analysis.md and enforced in CI).

### Neutral

- `packages/source-adapters → packages/domain-python` is a compile-time dependency. At runtime, both are installed in `apps/worker/`. This is standard Python packaging.

---

## Migration Impact

### No database migration required.

### Application changes (Week 1, monorepo scaffolding):
- Update `project-analysis.md` §4.1 with the complete dependency graph.
- Add `.importlinter` configuration to repository root.
- Add `import-linter` to CI pipeline.

### Package structure (Week 1):
- `packages/domain-python/chronoarb/domain/source_adapters/` directory with `protocol.py` and `types.py`.
- `packages/source-adapters/` imports from `chronoarb.domain.source_adapters`.

---

## Testing Implications

### CI enforcement
- `import-linter` check passes: domain-python does not import from source-adapters or apps.
- `import-linter` check passes: source-adapters does not import from apps.
- `import-linter` check passes: no cross-app imports.

### Domain tests
- `SourceAdapter` Protocol is abstract — tested through adapter implementations.
- Domain types (`SourceItemRef`, `RawObservation`, `ParsedListing`) have unit tests for construction and validation.

### Adapter tests
- Each adapter's import of `from chronoarb.domain.source_adapters import SourceAdapter` resolves correctly.
- Adapter implementation satisfies the Protocol (verified by `isinstance(adapter, SourceAdapter)` in test fixtures).

---

## References

- ADR-0001 D9: Source Adapter Isolation
- ADR-0001 D11: Monorepo Structure
- project-analysis.md §4.1: Module Dependency Rules (to be updated)
- AGENTS.md §5: Reuse and Duplication Rules
- Architecture Review: MAJOR-04
