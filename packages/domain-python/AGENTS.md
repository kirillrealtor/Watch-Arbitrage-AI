# ChronoArb Domain Package — Engineering Rules

This file adds module-specific rules to the root `AGENTS.md`. It cannot weaken security, tenant isolation, financial correctness, or SRS requirements.

## Module-specific rules

- This package contains PURE domain logic: value objects, entities, domain services, Protocol interfaces, and policies.
- It MUST NOT import from `packages/source-adapters` or any `apps/` package.
- All financial values must use `Decimal` from the standard library. `float` is prohibited for money.
- All monetary values must carry an explicit ISO 4217 currency code.
- Protocol interfaces (e.g., `SourceAdapter`) define contracts for external dependencies. Implementations live in `packages/source-adapters/`.
- ULID generation must use a type prefix (e.g., `org_`, `usr_`, `lst_`) for human-readability and log grepability.
- Domain errors must extend a common `DomainError` base class.

## Technology

- **Language:** Python 3.13+
- **Type checking:** mypy (strict)
- **Money:** `decimal.Decimal`
- **IDs:** ULID with prefix
