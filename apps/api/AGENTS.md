# ChronoArb API Module — Engineering Rules

This file adds module-specific rules to the root `AGENTS.md`. It cannot weaken security, tenant isolation, financial correctness, or SRS requirements.

## Module-specific rules

- FastAPI routes must NOT contain business logic — only validation, auth, service call, response mapping.
- Every service call in a route handler must pass an explicit `organization_id` obtained from the authenticated request context.
- Pydantic request/response schemas must use `snake_case` and match the API contract in `docs/architecture/api-design.md`.
- All route handlers must be async.
- Health check endpoints (`/health`, `/health/ready`) must be excluded from auth middleware.
- Transaction boundaries are managed at the application service layer, not in repositories.

## Technology

- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0 (async)
- **Migrations:** Alembic
- **Validation:** Pydantic v2 (strict mode)
- **DB driver:** asyncpg
