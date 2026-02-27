# ═══════════════════════════════════════════════════════
# DentalOS Development Makefile
# ═══════════════════════════════════════════════════════

.PHONY: help setup start stop restart logs status \
        db-migrate db-migrate-tenant db-revision db-downgrade db-current \
        db-keys db-seed db-reset onboard \
        backend frontend worker \
        test test-unit test-integration test-cov \
        lint format typecheck quality \
        load-seed load-test load-test-ui load-test-conflict load-test-pool \
        clean

# ─── Help ─────────────────────────────────────────────
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

# ─── Setup (first time) ──────────────────────────────
setup: ## First-time setup: install deps, start infra
	@echo "Setting up DentalOS development environment..."
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	cd backend && uv sync
	@echo ""
	@echo "Setup complete. Copy backend/.env.example to backend/.env, then run 'make backend'."

# ─── Infrastructure ───────────────────────────────────
start: ## Start Docker infrastructure (postgres, redis, rabbitmq, minio)
	docker compose up -d
	@echo "Infrastructure started. Services:"
	@echo "  PostgreSQL:    localhost:5432"
	@echo "  PostgreSQL Test: localhost:5433"
	@echo "  Redis:         localhost:6379"
	@echo "  RabbitMQ:      localhost:5672  (UI: http://localhost:15672)"
	@echo "  MinIO:         localhost:9000  (Console: http://localhost:9001)"

stop: ## Stop Docker infrastructure
	docker compose down

restart: ## Restart Docker infrastructure
	docker compose restart

logs: ## Tail Docker container logs
	docker compose logs -f --tail=100

status: ## Show Docker container status
	docker compose ps

# ─── Database ─────────────────────────────────────────
db-migrate: ## Run database migrations
	cd backend && uv run alembic upgrade head

db-revision: ## Create new migration (usage: make db-revision MSG="description")
	cd backend && uv run alembic revision --autogenerate -m "$(MSG)"

db-downgrade: ## Rollback one migration
	cd backend && uv run alembic downgrade -1

db-current: ## Show current migration state
	cd backend && uv run alembic current

db-keys: ## Generate JWT RS256 key pair
	cd backend && uv run python scripts/generate_keys.py

db-migrate-tenant: ## Run tenant migrations (usage: make db-migrate-tenant SCHEMA=tn_demodent)
	cd backend && uv run alembic -c alembic_tenant/alembic.ini -x schema=$(SCHEMA) upgrade head

db-seed: ## Seed dev database (plans, tenant, users, patients)
	cd backend && uv run python scripts/seed_dev.py

db-reset: ## Reset database completely (WARNING: destroys all data)
	docker compose down -v && docker compose up -d
	@echo "Waiting for services..."
	@sleep 5
	$(MAKE) db-migrate
	$(MAKE) db-seed

onboard: db-keys db-migrate db-seed ## First-time DB setup (run after 'make setup' + .env config)

# ─── Application Servers ─────────────────────────────
backend: ## Start FastAPI dev server (port 8000)
	cd backend && uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Start Next.js dev server (port 3000)
	cd frontend && npm run dev

worker: ## Start RabbitMQ background worker
	cd backend && uv run python -m app.worker.main

# ─── Testing ─────────────────────────────────────────
test: ## Run all backend tests
	cd backend && uv run pytest

test-unit: ## Run backend unit tests only
	cd backend && uv run pytest -m unit

test-integration: ## Run backend integration tests only
	cd backend && uv run pytest -m integration

test-cov: ## Run tests with HTML coverage report
	cd backend && uv run pytest --cov-report=html

test-file: ## Run specific test file (usage: make test-file FILE=tests/path/to/test.py)
	cd backend && uv run pytest $(FILE) -v

# ─── Code Quality ────────────────────────────────────
lint: ## Run ruff linter on backend
	cd backend && uv run ruff check app/ tests/

format: ## Auto-format backend code
	cd backend && uv run ruff format app/ tests/

typecheck: ## Run mypy type checker on backend
	cd backend && uv run mypy app/

quality: lint typecheck ## Run all quality checks (lint + typecheck)

# ─── Load Testing ───────────────────────────────────
load-seed: ## Seed load test data (10 tenants, 2500 patients)
	cd backend && uv run python -m load_tests.seed_load

load-test: ## Run 500-user load test for 30 min (headless)
	cd backend && uv run locust -f load_tests/locustfile.py \
		--headless -u 500 -r 25 -t 30m \
		--html load_tests/reports/report_$$(date +%Y%m%d_%H%M%S).html \
		--csv load_tests/reports/stats

load-test-ui: ## Run load test with web UI (localhost:8089)
	cd backend && uv run locust -f load_tests/locustfile.py

load-test-conflict: ## Run 100-concurrent appointment booking test
	cd backend && uv run locust -f load_tests/locustfile.py ConflictBookingUser \
		--headless -u 100 -r 100 -t 30s \
		--html load_tests/reports/conflict_$$(date +%Y%m%d_%H%M%S).html

load-test-pool: ## Run DB connection pool stress test
	cd backend && LOCUST_SHAPE=pool_stress uv run locust -f load_tests/locustfile.py PoolStressUser \
		--headless -t 5m \
		--html load_tests/reports/pool_stress_$$(date +%Y%m%d_%H%M%S).html

# ─── Cleanup ─────────────────────────────────────────
clean: ## Remove generated files, caches, volumes
	docker compose down -v
	rm -rf backend/.venv backend/__pycache__ backend/.pytest_cache backend/htmlcov
	rm -rf frontend/node_modules frontend/.next
	@echo "Clean complete. Run 'make setup' to start fresh."
