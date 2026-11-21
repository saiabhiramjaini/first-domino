# First Domino

Find the first domino: the step where your AI agent's run started to fall. Proven, not guessed.

First Domino takes a failed agent run, re-runs the agent from its own save points, binary-searches for the step where the run became doomed, then fixes that one step and replays to prove it.

> Status: skeleton. Layout, rules, contract and work plan only. No product code yet.

## Repository layout

```
first-domino/
  AGENTS.md, CLAUDE.md   repo-wide rules for every agent and person
  docs/
    CONTRACT.md          the API, worker protocol, engine ports and SDK surface
    PARALLEL_WORK.md     workstreams, file ownership, milestones, git
    briefs/              the starting prompt for each workstream's agent
    status/              one status file per workstream
    ARCHITECTURE.md      how the pieces fit
    DECISIONS.md         what is decided and what is open
  api/openapi.json       the generated HTTP contract, shared by both halves
  backend/               Python: API, engine, database, SDK, demo agent, scripts
  frontend/              Next.js web app (not scaffolded yet)
  .github/workflows/     backend.yml and frontend.yml
```

The backend and the frontend are fully separate: each has its own tooling, dependencies, rules, environment file and CI. They meet only at the HTTP contract.

## Getting started

- Backend: see [`backend/README.md`](./backend/README.md).
- Frontend: see [`frontend/AGENTS.md`](./frontend/AGENTS.md).

After `git init`, run `uv run --project backend pre-commit install` once, so the git hooks for both halves run.

## Working in parallel

Start each workstream by opening a new agent chat in `backend/` or `frontend/` and pasting its brief from [`docs/briefs/`](./docs/briefs/README.md). [`docs/PARALLEL_WORK.md`](./docs/PARALLEL_WORK.md) explains ownership, milestones and merging.

## Read next

- [`AGENTS.md`](./AGENTS.md) for the repo-wide rules
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for how the pieces fit
- [`docs/DECISIONS.md`](./docs/DECISIONS.md) for what is decided and what is open
