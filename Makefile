# LapTimeSimulator_CopaTruck — developer entry points.
# Mirrors the Makefile convention used in LapTimeSimulator_SARU.
.DEFAULT_GOAL := help
COMPOSE := docker compose

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

check-env: ## Verify .env exists (copy from .env.example yourself)
	@test -f .env || (echo "ERROR: .env not found — run: cp .env.example .env" && exit 1)

build: check-env ## Build the app image
	$(COMPOSE) build

up: check-env ## Start db + Streamlit app in the background (dev: hot-reload via override)
	$(COMPOSE) up -d

up-fg: check-env ## Start the stack in the foreground (Ctrl-C to stop)
	$(COMPOSE) up

down: ## Stop the stack (keep volumes)
	$(COMPOSE) down

down-clean: ## Stop the stack AND remove volumes (drops the database!)
	$(COMPOSE) down -v

ps: ## Show service status
	$(COMPOSE) ps

logs: ## Tail logs for all services
	$(COMPOSE) logs -f --tail=100

logs-app: ## Tail logs for the Streamlit app
	$(COMPOSE) logs -f --tail=100 app

db-shell: check-env ## Open psql inside the db container
	$(COMPOSE) exec db sh -c 'psql -U $$POSTGRES_USER -d $$POSTGRES_DB'

seed: check-env ## Populate Postgres with the fleet presets from data/vehicle_models.json
	$(COMPOSE) exec app python src/database/seed_db.py

test: ## Run the pytest suite locally (.venv)
	.venv/bin/python -m pytest -q

run-local: check-env ## Run Streamlit outside Docker, pointed at the compose db
	@set -a; . ./.env; set +a; \
	DB_HOST=localhost .venv/bin/python -m streamlit run src/visualization/interface.py

.PHONY: help check-env build up up-fg down down-clean ps logs logs-app db-shell seed test run-local
