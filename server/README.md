# First Domino backend

The Python half of First Domino: the control plane API, the engine, the database, and the public SDK (`first-domino` on PyPI). In production the API runs as a Docker container on EC2 (`docs/DEPLOY.md`).

## Layout

```
server/
  AGENTS.md, CLAUDE.md   Python rules (the repo-root AGENTS.md also applies)
  REVIEW.md              self-review checklist
  .claude/               path-scoped rules, the ruff hooks and the code-design skill
  packages/
    fd-shared/           typed models, enums, errors, settings base, logging
    fd-database/         Postgres tables and repositories
    fd-engine/           search, verify, fallback, explain, group (the core)
    fd-api/              FastAPI control plane: auth, ingest, jobs, diagnoses, causes
    first-domino/        public Python SDK: @fd.entrypoint, HTTP capture, replay worker
  api/openapi.json       the generated HTTP contract
  deploy/                production config, the EC2 scripts and nginx config
  compose.yaml           local Postgres
  Dockerfile             the API image
  Makefile               common commands
```

## Commands

Run from `server/`.

```bash
make install     # uv sync, all packages and dev tools
make db-up       # start local Postgres
make api         # run the API on :8000 with reload
make dev-key     # print an API key for local work without the web app
make check       # ruff, pyright, pytest
make fix         # ruff auto-fix and format
make openapi     # write api/openapi.json
make sdk-models  # generate the SDK models from api/openapi.json
```

The full list is `make help`.

## Requirements

- Python 3.12 and `uv`
- Docker, running, for local Postgres
- `jq`, used by the agent lint hook in `.claude/hooks/`
- An OpenAI API key, set in `.env` (copy `.env.example`)
