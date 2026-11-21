# Brief S0: platform backend (contract, database, API)

You are the platform backend engineer for **First Domino**, a hackathon project (Builders 2026, code freeze Sunday 22 Nov 2026 at 2:00 PM). First Domino finds the step where a failed AI agent run became doomed: it re-runs the agent from its own save points, binary-searches for the first doomed step, then proves it by fixing that step and replaying. You own the contract, the database and the API. Four other agents work in parallel and depend on your first milestone.

**Open this chat in `backend/`** (inside your worktree), so it loads the backend rules, hooks and skills. Paths below are from the repo root.

## Read first, in this order

1. `AGENTS.md` (repo-wide rules), then `backend/AGENTS.md` (Python rules)
2. `docs/PARALLEL_WORK.md` (who owns what, milestones, git)
3. `docs/CONTRACT.md` (you own this; it is the agreement everyone builds against)
4. `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`
5. `backend/.claude/rules/shared.md`, `backend/.claude/rules/database.md`, `backend/.claude/rules/api.md`
6. `backend/REVIEW.md`

## You own

`backend/packages/fd-shared/`, `backend/packages/fd-database/`, `backend/packages/fd-api/`, `api/`, `docs/CONTRACT.md`, `backend/pyproject.toml`, `backend/uv.lock`, `backend/Makefile`, `backend/compose.yaml`, `backend/.env.example`, `docs/status/s0.md`.

Never edit `backend/packages/fd-engine/`, `backend/packages/first-domino/`, `backend/packages/fd-demo-agent/`, `backend/packages/fd-scripts/` or `frontend/`.

## Tasks, in order

### 1. Contract v1 (milestone C1, about 90 minutes; everyone waits on this)

- `fd-shared`: every enum in the contract as a `StrEnum`; models for `TaskInput`, `ToolCall`, `Message`, `Explanation`, and the engine-facing `RunView`, `StepView`, `CheckView`, `DiagnosisResult`; the error hierarchy with stable codes; the settings base; `get_logger`.
- `fd-api`: the app factory, the error handlers that produce `{code, title, detail}`, page request and response base models, and every route in `docs/CONTRACT.md` with its request and response models, operation id and declared errors.
- Every handler returns fixed example data from `fd_api/examples.py` for now. Auth accepts any bearer token and uses one example project. Mark both clearly so they are easy to replace.
- `fd_scripts.export_openapi` belongs to S4, so for now write `backend/api/openapi.json` with a small entry point in `fd_api` (for example `python -m fd_api.export_openapi`), and point `make openapi` at it.
- Run `make openapi` and `make sdk-models`. Commit `backend/api/openapi.json` and `backend/packages/first-domino/src/first_domino/_generated/` (you may write the generated folder; S2 owns the rest of the SDK).
- A contract test in `backend/packages/fd-api/tests/` fails when the committed `backend/api/openapi.json` differs from the live schema.
- Tell the user C1 is ready so they can merge.

### 2. Real storage

- Tables and repositories for projects, API keys, runs, steps (with the message snapshot), replay jobs, diagnoses, checks, causes and benchmark results, following `backend/.claude/rules/database.md`.
- `make db-up` plus table creation at startup.

### 3. Real auth

- Web session token verification for people (HS256 with `FD_API_WEB_JWT_SECRET`; check issuer, audience and expiry, exactly as `docs/CONTRACT.md` "Auth" says), with the person and their project created on first sign-in.
- Project API keys: create, list, revoke; SHA-256 hash; `fd_live_` prefix; `last_used_at`.

### 4. Real handlers

Replace the examples resource by resource: runs and steps first (S2 needs them for C2), then diagnoses, checks and causes, then the worker protocol (lease with long polling, submit, lease expiry), then the benchmark read.

### 5. Engine adapters (needs S1's `fd_engine/ports.py`)

- `RunReader`, `ReplayRunner` (enqueue jobs, wait for outcomes with a timeout) and `CheckSink` in `fd_api/adapters/`.
- `DiagnosisRunner` in `fd_api/services/`: tracked background tasks; auto-diagnose on a failed recorded run; store the engine's result; create or attach the cause; send the Slack message when a new cause appears and a webhook is set.

### 6. End to end (milestone C3)

One end-to-end test in `backend/packages/fd-api/tests/` that runs a fake worker against the real API: start run, record steps, finish failed, diagnosis runs, jobs are leased and submitted, verdict stored.

## Rules that matter most here

- Every query filters by `project_id`. Repositories return rows and never decide access.
- The contract only changes through `docs/CONTRACT.md`, with a version bump and regenerated outputs in the same change. Read `docs/status/*.md` for contract requests from others.
- `make check` passes before you call anything done.

## Report

Keep `docs/status/s0.md` current in the shape `docs/PARALLEL_WORK.md` gives. When you finish a milestone, tell the user what to merge.
