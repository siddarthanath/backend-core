.PHONY: install dev run test migrate-new migrate-up migrate-down migrate-reset lint fmt help

# ── Config ────────────────────────────────────────────────────────────────────
APP := src.main:app

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  install        Install production dependencies"
	@echo "  dev            Install all dependencies including dev/test"
	@echo "  run            Start uvicorn dev server with hot reload"
	@echo ""
	@echo "  migrate-new    Generate a new migration  (m=name required)"
	@echo "  migrate-up     Apply all pending migrations"
	@echo "  migrate-down   Roll back all migrations to base"
	@echo "  migrate-reset  Downgrade to base then upgrade to head (full reset)"
	@echo ""
	@echo "  test           Run all tests"
	@echo "  lint           Run ruff linter"
	@echo "  fmt            Run ruff formatter"
	@echo ""

# ── Install ───────────────────────────────────────────────────────────────────
install:
	@echo "-> Installing production dependencies..."
	pip install .

dev:
	@echo "-> Installing all dependencies (including dev)..."
	pip install -e ".[dev]"

# ── Server ────────────────────────────────────────────────────────────────────
run:
	@echo "-> Starting dev server at http://localhost:8000 ..."
	uvicorn $(APP) --reload

# ── Migrations ────────────────────────────────────────────────────────────────
migrate-new:
	@if [ -z "$(m)" ]; then echo "Usage: make migrate-new m=your_migration_name"; exit 1; fi
	@echo "-> Generating migration: $(m)"
	alembic revision --autogenerate -m "$(m)"

migrate-up:
	@echo "-> Applying all migrations..."
	alembic upgrade head

migrate-down:
	@echo "-> Rolling back all migrations to base..."
	alembic downgrade base

migrate-reset:
	@echo "-> Resetting database (down then up)..."
	alembic downgrade base
	alembic upgrade head

# ── Quality ───────────────────────────────────────────────────────────────────
test:
	@echo "-> Running tests..."
	pytest tests/ -v

lint:
	@echo "-> Running linter..."
	ruff check src/ tests/

fmt:
	@echo "-> Formatting code..."
	ruff format src/ tests/
