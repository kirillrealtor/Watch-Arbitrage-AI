# ChronoArb — Development Makefile
#
# PostgreSQL migrations run via `docker exec` because Python 3.14 has
# unresolved async driver incompatibilities with asyncpg and psycopg.
# See: ADR-0009 (local database development strategy)
#
# Alembic generates PostgreSQL DDL via `--sql` mode into a temp file,
# then the SQL is applied via psql inside the Docker container. This
# preserves the hand-written migration workflow and Alembic version
# tracking through the alembic_version table.

PG_CONTAINER := chronoarb-pg
PG_DATABASE  := chronoarb
PG_USER      := postgres
PG_URL       := postgresql+asyncpg://postgres:chronoarb@localhost:5432/chronoarb
MIGRATE_TMP  := /tmp/chronoarb_migrate.sql

export CHRONOARB_DATABASE_URL = $(PG_URL)
export PATH := $(shell pwd)/.venv/bin:$(PATH)

.PHONY: db-migrate db-reset db-rollback db-status db-revision

## Apply all pending migrations to PostgreSQL
db-migrate:
	@echo "=== Generating migration SQL ==="
	@alembic upgrade head --sql 2>/dev/null > $(MIGRATE_TMP)
	@docker exec -i $(PG_CONTAINER) psql -U $(PG_USER) -d $(PG_DATABASE) -q < $(MIGRATE_TMP)
	@rm -f $(MIGRATE_TMP)
	@echo ""
	@echo "=== Current schema ==="
	@docker exec $(PG_CONTAINER) psql -U $(PG_USER) -d $(PG_DATABASE) -c "\dt"

## Reset database (drop everything, re-apply all migrations)
db-reset: db-clean
	@echo "=== Re-applying all migrations ==="
	@alembic upgrade head --sql 2>/dev/null > $(MIGRATE_TMP)
	@docker exec -i $(PG_CONTAINER) psql -U $(PG_USER) -d $(PG_DATABASE) -q < $(MIGRATE_TMP)
	@rm -f $(MIGRATE_TMP)
	@echo ""
	@echo "=== Current schema ==="
	@docker exec $(PG_CONTAINER) psql -U $(PG_USER) -d $(PG_DATABASE) -c "\dt"

## Drop all tables, ENUMs, and alembic tracking (destructive)
db-clean:
	@echo "=== Dropping all database objects ==="
	@docker exec $(PG_CONTAINER) psql -U $(PG_USER) -d $(PG_DATABASE) -c \
		"DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO $(PG_USER);"
	@echo "=== Database cleaned ==="

## Rollback one migration (interactive — prompts for target revision)
db-rollback:
	@echo "=== Current revision ==="
	@docker exec $(PG_CONTAINER) psql -U $(PG_USER) -d $(PG_DATABASE) -c "SELECT version_num FROM alembic_version;"
	@read -p "Downgrade target revision [base]: " target; \
		target=$${target:-base}; \
		current=$$(docker exec $(PG_CONTAINER) psql -U $(PG_USER) -d $(PG_DATABASE) -t -c "SELECT version_num FROM alembic_version;" | tr -d '[:space:]'); \
		echo "=== Downgrading from $$current to $$target ==="; \
		alembic downgrade $$current:$$target --sql 2>/dev/null > $(MIGRATE_TMP) && \
		docker exec -i $(PG_CONTAINER) psql -U $(PG_USER) -d $(PG_DATABASE) -q < $(MIGRATE_TMP) && \
		rm -f $(MIGRATE_TMP)

## Show current migration state
db-status:
	@echo "=== Alembic version ==="
	@docker exec $(PG_CONTAINER) psql -U $(PG_USER) -d $(PG_DATABASE) -c "SELECT * FROM alembic_version;"
	@echo "=== Tables ==="
	@docker exec $(PG_CONTAINER) psql -U $(PG_USER) -d $(PG_DATABASE) -c "\dt"
	@echo "=== ENUMs ==="
	@docker exec $(PG_CONTAINER) psql -U $(PG_USER) -d $(PG_DATABASE) -c "SELECT typname FROM pg_type WHERE typtype='e';"

## Generate a new Alembic revision (hand-written, no autogenerate)
db-revision:
	@read -p "Revision message: " msg; \
		alembic revision -m "$$msg"
	@echo "=== New revision created ==="
	@ls -t alembic/versions/*.py | head -1
