.DEFAULT_GOAL := help
SDK_GENERATED := packages/first-domino/src/first_domino/_generated/models.py

.PHONY: help install lint fix typecheck test check db-up db-down api dev-key worker openapi sdk-models

help: ## List commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

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

worker: ## Run the demo customer's replay worker
	uv run python -m fd_demo_agent.worker

openapi: ## Write ../api/openapi.json from the API
	uv run python -m fd_api.export_openapi

sdk-models: ## Generate SDK wire models from ../api/openapi.json
	uv run datamodel-codegen --input ../api/openapi.json --input-file-type openapi \
		--output $(SDK_GENERATED) --output-model-type pydantic_v2.BaseModel \
		--use-annotated --use-standard-collections --use-union-operator \
		--target-python-version 3.12 --disable-timestamp --formatters builtin \
		--custom-file-header '"""Wire models generated from api/openapi.json by make sdk-models. Do not edit."""'
	# The root pre-commit hook formats every staged file, generated ones included.
	uv run ruff format $(SDK_GENERATED)
