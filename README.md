# First Domino

Find the first domino: the step where your AI agent's run started to fall. Proven, not guessed.

First Domino takes a failed agent run, re-runs the agent from its own save points, binary-searches for the step where the run became doomed, then fixes that one step and replays to prove it.

> Status: built for Builders 2026 and running locally (web on :3000, API on :8000).

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
  server/                Python: API, engine, database, SDK, demo agent, scripts
  client/                Next.js web app
  .github/workflows/     server.yml and client.yml
```

The server and the client are fully separate: each has its own tooling, dependencies, rules, environment file and CI. They meet only at the HTTP contract (`server/api/openapi.json`).

## Run it locally

Needs Python 3.12 with `uv`, Bun, Docker (running) and `jq`.

1. Environment files. Copy `server/.env.example` to `server/.env` and fill in `OPENAI_API_KEY`, `FD_ENGINE_STRONG_MODEL`, `FD_DEMO_AGENT_MODEL` and `FD_API_WEB_JWT_SECRET`. Copy `client/.env.example` to `client/.env.local` and fill in the Google OAuth client, `AUTH_SECRET`, and `API_JWT_SECRET` (the same value as `FD_API_WEB_JWT_SECRET`).
2. Install: `make install` in `server/`, `bun install` in `client/`.
3. Database and API, from `server/`: `make db-up`, then `make api` (port 8000; it creates the tables on start).
4. Web app, from `client/`: `bun run dev` (port 3000). Sign in with Google once.
5. Demo customer, from `server/`: `make seed-demo EMAIL=<your Google email>` prints an API key; put it in `server/.env` as `FIRST_DOMINO_API_KEY`, then start `make worker` in its own terminal.
6. Try it: `make demo-live` records a failing call and prints its link. Open it and watch the diagnosis.

Checks: `make check` in `server/`, `bun run check` in `client/`.

## Getting started as a contributor

- Server: see [`server/README.md`](./server/README.md).
- Client: see [`client/AGENTS.md`](./client/AGENTS.md).

Git hooks are Husky scripts in `client/.husky/`. Running `bun install` in `client/` turns them on (its `prepare` script points git at them). The pre-commit hook runs ruff on staged backend files and Prettier on staged frontend files; the commit-msg hook checks `type: subject`.

## Working in parallel

Start each workstream by opening a new agent chat in `server/` or `client/` and pasting its brief from [`docs/briefs/`](./docs/briefs/README.md). [`docs/PARALLEL_WORK.md`](./docs/PARALLEL_WORK.md) explains ownership, milestones and merging.

## Read next

- [`AGENTS.md`](./AGENTS.md) for the repo-wide rules
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for how the pieces fit
- [`docs/DECISIONS.md`](./docs/DECISIONS.md) for what is decided and what is open
