# Brief S3: web app

You are the frontend engineer for **First Domino**, a hackathon project (Builders 2026, code freeze Sunday 22 Nov 2026 at 2:00 PM). First Domino finds the step where a failed AI agent run became doomed: it re-runs the agent from its own save points, binary-searches for the first doomed step, then proves it by fixing that step and replaying. You build the web app that judges click through. It is a frontend-only Next.js app that talks to the First Domino API (FastAPI) over HTTP.

**Open this chat in `client/`** (inside your worktree), so it loads the frontend rules. Paths below are from the repo root.

## Read first, in this order

1. `client/AGENTS.md`, then `client/STANDARDS.md` and `client/REVIEW.md` (your rules)
2. `AGENTS.md` at the repo root (shared rules: git, no copied code, hackathon constraints)
3. `docs/PARALLEL_WORK.md`
4. `docs/CONTRACT.md` (every screen reads from these operations)
5. `docs/ARCHITECTURE.md`

## You own

`client/`, `.github/workflows/client.yml` and `docs/status/s3.md`. Never edit anything else. The API contract changes only through S0; put requests in your status file.

## Tasks, in order

### 1. Scaffold (no backend needed)

Follow "Scaffold" in `client/STANDARDS.md` exactly. `client/` already holds the rule files, so scaffold into a temporary folder and move the result in without overwriting them.

Done when `bun run check` passes and `/api/health` answers.

### 2. Shell and sign-in

- Google sign-in with NextAuth, as `client/STANDARDS.md` "Auth" says; signed-out visitors see the landing page only.
- App shell: sidebar with Failures, Root causes, Benchmark, Settings; the project name; the user menu.
- Landing page: the product in one sentence, the "first domino" idea, a sign-in button.

### 3. API layer (after contract v1)

- Generate the typed client and Zod schemas from `../server/api/openapi.json` into `src/api/generated/`.
- One React Query hook per operation in `src/hooks/api/` (`use-list-runs`, `use-get-diagnosis`, `use-create-diagnosis`, ...), sending the web session token.
- Until real handlers land, the API answers with example data, so screens work from the start.

### 4. Screens (milestone C2 with example data, C4 with real data)

| Screen | Route | Reads |
| --- | --- | --- |
| Failures inbox | `/failures` | `countRuns`, `countCauses`, `countDiagnoses`, `listCauses`, `listRuns` (failed) |
| Run diagnosis (the hero screen) | `/runs/[runId]` | `getRun`, `listSteps`, `getDiagnosis`, `listChecks`; `createDiagnosis` |
| Root causes | `/causes`, `/causes/[causeId]` | `listCauses`, `getCause`, `listDiagnoses` by cause |
| Benchmark | `/benchmark` | `getLatestBenchmark` |
| Onboarding and settings | `/settings` | `getProjectSelf`, API keys, Slack webhook, SDK snippet |

The run diagnosis screen shows: the step strip (search range in one tone, the first domino in another, ruled-out steps muted), the live list of checks with their pass counts, and the verdict card with the original and fixed step side by side, the explanation and the suggested fix. It polls every second while the diagnosis is running.

### 5. Polish (before C6)

Empty states, loading skeletons, error states, copy pass, phone width check, the demo path rehearsed end to end.

## Report

Keep `docs/status/s3.md` current in the shape `docs/PARALLEL_WORK.md` gives.
