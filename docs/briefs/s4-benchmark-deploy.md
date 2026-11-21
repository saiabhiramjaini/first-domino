# Brief S4: benchmark, deploy and demo assets

You join **First Domino** after the first end-to-end run works (milestone C3). First Domino finds the step where a failed AI agent run became doomed and proves it by replay. Your job: the numbers that prove it works, the public deployment, and the demo safety net. Code freeze is Sunday 22 Nov 2026 at 2:00 PM.

**Open this chat in `backend/`** (inside your worktree), so it loads the backend rules, hooks and skills. Paths below are from the repo root.

## Read first, in this order

1. `AGENTS.md` (repo-wide rules), then `backend/AGENTS.md` (Python rules)
2. `docs/PARALLEL_WORK.md`
3. `docs/ARCHITECTURE.md`, `docs/CONTRACT.md`, `docs/DECISIONS.md`
4. `backend/.claude/rules/scripts.md`
5. `docs/status/*.md` (where everyone else is)

## You own

`backend/packages/fd-scripts/`, `deploy/`, `.github/workflows/` (except `frontend.yml`, which S3 owns) and `docs/status/s4.md`. Move `make openapi` to `fd_scripts.export_openapi` only after agreeing it with S0 in your status file.

## Tasks, in order

### 1. Labelled dataset (milestone C4)

`make_dataset.py`: run the demo agent on every task, keep the successful runs, plant each bug type at its step, let the agent continue, keep the runs that end in failure with the true step as the label. Target 30 to 40 labelled failures.

### 2. Benchmark (milestone C4)

`benchmark.py`: score First Domino and the read-the-trace baseline on the same labelled runs with the same model. Report exact step accuracy, within one step, verified rate, mean cost and mean seconds. Write results to the database so `getLatestBenchmark` shows them, and to `backend/data/benchmarks/`.

### 3. Source guard test

`backend/packages/fd-scripts/tests/test_source_guards.py`: fail on a forbidden layer import, a mixed-value `dict` in a public signature, or a model id outside a settings module (see `backend/AGENTS.md`, "Tooling gates").

### 4. Deploy (milestone C5)

- A Dockerfile for the API and the demo worker (S3 provides `frontend/Dockerfile`), a production compose file in `deploy/` with Postgres, API, web and Caddy for HTTPS on a sslip.io name.
- One EC2 instance. Secrets from an `.env` on the instance, never in the repo.
- The demo worker runs as its own container next to the stack, as a customer's would.
- Stop at 9:30 AM Sunday if it is not working; a recorded demo is an accepted submission.

### 5. Demo safety net (before C7)

Seed data so the inbox is never empty, a backup screen recording of the full demo, and the README results section with the benchmark numbers.

## Report

Keep `docs/status/s4.md` current in the shape `docs/PARALLEL_WORK.md` gives.
