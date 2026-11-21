.DEFAULT_GOAL := help
SDK_GENERATED := packages/first-domino/src/first_domino/_generated/models.py

.PHONY: help install lint fix typecheck test check db-up db-down api dev-key seed-demo worker demo-live demo-live-clean customer-worker customer-demo openapi sdk-models

help: ## List commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-16s %s\n", $$1, $$2}'

install: ## Install all packages and dev tools
	uv sync

lint: ## Check lint and formatting
	uv run ruff check --no-fix .
	uv run ruff format --check .

fix: ## Auto-fix lint and format
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## Type-check with pyright
	uv run pyright

test: ## Run tests (no tests yet is not a failure)
	uv run pytest || [ $$? -eq 5 ]

check: lint typecheck test ## Everything a change must pass

db-up: ## Start local Postgres
	docker compose up -d --wait postgres

db-down: ## Stop local Postgres
	docker compose down

api: ## Run the API with reload
	uv run uvicorn fd_api.main:create_app --factory --reload --port 8000

dev-key: ## Print a new API key for the local developer's project (needs db-up)
	@uv run python -m fd_api.dev_api_key

seed-demo: ## Give EMAIL the "Equal AI (demo)" project and print its worker API key
	@test -n "$(EMAIL)" || (echo "usage: make seed-demo EMAIL=person@example.com" >&2; exit 2)
	@uv run python -m fd_api.seed_demo --email "$(EMAIL)"

worker: ## Run the demo customer's replay worker
	uv run python -m fd_demo_agent.worker

demo-live: ## Record one planted-bug call (BUG=b02) and print its web link
	uv run python -m fd_demo_agent.demo_live --bug $(or $(BUG),b02)

demo-live-clean: ## Record one passing call and print its web link
	uv run python -m fd_demo_agent.demo_live --clean

# Acting as a real customer of the live product: settings come from .env.customer
# (copy customer.env.example), so the agent talks to the deployed API, not localhost.
CUSTOMER_ENV ?= .env.customer
CUSTOMER_RUN = test -f $(CUSTOMER_ENV) || { echo "copy customer.env.example to $(CUSTOMER_ENV) first" >&2; exit 2; }; set -a; . ./$(CUSTOMER_ENV); set +a;

customer-worker: ## As the customer: run the replay worker against the live API
	@$(CUSTOMER_RUN) uv run python -m fd_demo_agent.worker

customer-demo: ## As the customer: record one planted-bug call (BUG=b02) on the live site
	@$(CUSTOMER_RUN) uv run python -m fd_demo_agent.demo_live --bug $(or $(BUG),b02)

openapi: ## Write api/openapi.json from the API
	uv run python -m fd_api.export_openapi

sdk-models: ## Generate SDK wire models from api/openapi.json
	uv run datamodel-codegen --input api/openapi.json --input-file-type openapi \
		--output $(SDK_GENERATED) --output-model-type pydantic_v2.BaseModel \
		--use-annotated --use-standard-collections --use-union-operator \
		--target-python-version 3.12 --disable-timestamp --formatters builtin \
		--custom-file-header '"""Wire models generated from api/openapi.json by make sdk-models. Do not edit."""'
	# Keep the generated models ruff-formatted so regenerating gives a stable diff.
	uv run ruff format $(SDK_GENERATED)
