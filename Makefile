.PHONY: dev seed test lint typecheck install clean help

# ── Development ───────────────────────────────────────────────────────────────

dev:           ## Start the full stack (API + frontend) via Docker Compose
	docker compose up --build

dev-api:       ## Start the API only (no Docker required)
	cd backend && pip install --no-build-isolation -e ".[dev]" -q && \
	mkdir -p data && uvicorn app.main:app --reload --port 8000

dev-frontend:  ## Start the frontend only
	cd frontend && npm install && npm run dev

# ── Database ──────────────────────────────────────────────────────────────────

seed:          ## Seed demo data into the database
	cd backend && python -m app.db.seed

migrate:       ## Apply Alembic migrations
	cd backend && alembic upgrade head

migration:     ## Create an Alembic migration, e.g. make migration msg="add table"
	cd backend && alembic revision --autogenerate -m "$(msg)"

# ── Testing ───────────────────────────────────────────────────────────────────

test:          ## Run all backend tests
	cd backend && pip install --no-build-isolation -e ".[dev]" -q && pytest -v

test-watch:    ## Run tests in watch mode
	cd backend && pytest -v --tb=short -x

# ── Linting & type checking ───────────────────────────────────────────────────

lint:          ## Lint backend with ruff
	cd backend && ruff check app tests

lint-fix:      ## Auto-fix lint issues
	cd backend && ruff check --fix app tests

typecheck:     ## Type-check backend with mypy
	cd backend && mypy app

# ── Installation ──────────────────────────────────────────────────────────────

install:       ## Install all dependencies
	cd backend && pip install --no-build-isolation -e ".[dev]"
	cd frontend && npm install

install-ocr:   ## Install Google Vision OCR dependency
	cd backend && pip install --no-build-isolation -e ".[ocr]"

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:         ## Remove database and cache files
	rm -rf backend/data backend/__pycache__ backend/app/**/__pycache__
	rm -rf backend/.pytest_cache backend/.mypy_cache
	rm -rf frontend/node_modules frontend/dist

help:          ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
