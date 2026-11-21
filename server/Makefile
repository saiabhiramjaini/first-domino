.DEFAULT_GOAL := help
SDK_GENERATED := packages/first-domino/src/first_domino/_generated/models.py
MIGRATIONS := packages/fd-database/src/fd_database/migrations/versions

.PHONY: help install lint fix typecheck test check db-up db-down migrate migration api dev-key seed-demo openapi sdk-models

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

migrate: ## Upgrade the database to the latest revision (the API also does at startup)
	uv run python -m fd_database.migrate upgrade

migration: ## Write a revision for the table changes: make migration MSG="add runs.note"
	@test -n "$(MSG)" || (echo 'usage: make migration MSG="add runs.note"' >&2; exit 2)
	uv run python -m fd_database.migrate revision --message "$(MSG)"
	# Keep new revisions ruff-clean; review each one before committing it.
	uv run ruff format $(MIGRATIONS)
	uv run ruff check --fix $(MIGRATIONS)

api: ## Run the API with reload
	uv run uvicorn fd_api.main:create_app --factory --reload --port 8000

dev-key: ## Print a new API key for the local developer's project (needs db-up)
	@uv run python -m fd_api.dev_api_key

seed-demo: ## Give EMAIL the "Call assistant (demo)" project and print an API key for it
	@test -n "$(EMAIL)" || (echo "usage: make seed-demo EMAIL=person@example.com" >&2; exit 2)
	@uv run python -m fd_api.seed_demo --email "$(EMAIL)"

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
