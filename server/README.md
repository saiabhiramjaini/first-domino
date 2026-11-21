# First Domino backend

The Python half of First Domino: the control plane API, the bisect engine, the database, and the public SDK.

> Status: layout only. No product code yet.

## Layout

```
server/
  AGENTS.md, CLAUDE.md   Python rules (the repo-root AGENTS.md also applies)
  REVIEW.md              self-review checklist
  .claude/               path-scoped rules, the ruff hooks and the code-design skill
  packages/
    fd-shared/           typed models, enums, errors, settings base, logging
    fd-database/         Postgres tables and repositories
    fd-engine/           bisect, verify, explain, group, baseline (the core)
    fd-api/              FastAPI control plane: auth, ingest, jobs, diagnoses
    first-domino/        public Python SDK: recorder, OpenAI wrapper, replay worker
  compose.yaml           local Postgres
  Makefile               common commands
```

## Commands

Run from `server/`.

```bash
make install     # uv sync, all packages and dev tools
make db-up       # start local Postgres
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
