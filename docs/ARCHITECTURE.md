# Architecture

## The idea in one paragraph

An agent run is a list of steps. Each step is one LLM turn plus the results of the tools it called. The SDK saves the message history after every step, so every step is a save point. To diagnose a failed run, the engine asks: "if we keep steps 1 to m exactly as recorded and re-run the rest, can the agent still succeed?" It binary-searches m to find the first save point from which the run always fails. That step is the first domino. The engine then rewrites that one step and replays to prove the fix flips failure into success.

## Components

```
 Browser ──► web (Next.js) ──► fd-api ──► Postgres (fd-database)
                                   │  ▲
                     uses engine   │  │ steps, results
                                   ▼  │
                               fd-engine        replay jobs
                                   │
 Customer side                      ▼
 ─────────────────────────────────────────────────────────────
 customer agent + first-domino SDK
   recorder ──── sends steps ──────────────► fd-api
   worker   ◄─── polls replay jobs ───────── fd-api
            └─── posts replay results ─────► fd-api
```

| Component | Runs where | Job |
| --- | --- | --- |
| `fd-api` | our cloud | Auth, ingest, job queue, diagnoses, causes, benchmark |
| `fd-engine` | inside `fd-api` | Decides which save point to test, reads results, proves the root cause |
| `fd-database` | our cloud | Postgres tables and repositories |
| `first-domino` SDK | customer side | Records steps; replay worker runs the customer's agent on command |
| `fd-demo-agent` | customer side (demo) | Plays the customer: its own agent, mock world and success check |
| `client/` | our cloud | Next.js app: sign-in, failures inbox, live diagnosis, causes, benchmark, settings |

## Why the replay runs on the customer side

The customer's agent needs its own code, secrets, tools and data. Running it on our side would mean taking their code and secrets. Instead the SDK worker runs next to their agent, polls our API for replay jobs and posts results back. It only connects outward, so the customer exposes no endpoint. This is the same model as Temporal workers and self-hosted CI runners.

## Flows

### 1. Record a run

1. The customer's agent runs with the SDK recorder (or the wrapped OpenAI client).
2. After each step the recorder sends the step to `fd-api`: index, model output, tool calls, tool results and the message snapshot.
3. When the run ends, the recorder posts the final result. The customer's success check marks it passed or failed.

### 2. Diagnose a failed run

1. A user clicks Diagnose, or auto-diagnose fires on a failure.
2. `fd-api` creates a diagnosis and starts the engine as a tracked background task.
3. The engine calls the `ReplayRunner` port: "replay run R from save point m, k times".
4. The API adapter turns that into replay jobs in Postgres and waits for their results.
5. The worker picks up the jobs, replays, runs the customer's success check and posts results.
6. The engine updates the search range and asks for the next check, until one step is left.
7. Verify: the engine asks the model to rewrite that step, then asks for replays from the fixed step.
8. Explain and group: the engine labels the cause and attaches it to a matching cause group.
9. The diagnosis is stored with every check, so the web app can show the search live.

### Replay job lifecycle

```
queued ──► leased ──► running ──► succeeded | failed
   ▲          │
   └──────────┘  lease expired (worker died): back to queued
```

- A worker leases a job for a fixed time. An expired lease returns the job to the queue.
- A job result is idempotent by job id. A repeated post does not count twice.

## The bisect rule

- `can_succeed(m)`: keep steps 1..m, replay the rest k times with the strong model. True if any replay succeeds.
- If `can_succeed(0)` is false, even a fresh run fails. Report a task or tool problem, not an agent step.
- Search invariant: the run can succeed from `lo - 1` and is doomed at `hi`. Halve until `lo == hi`.
- Verify: rewrite step `lo` and replay with the original agent model. Verified when at least the configured number of replays succeed.
- If verify fails, rank the nearby steps and try a fix on each. Report "multiple causes" when none flips the outcome.

All numbers in this rule (k, the verify threshold, the fallback window) are engine settings.

## Data model (planned)

| Table | Holds |
| --- | --- |
| `projects` | Tenant boundary. Every other table carries `project_id` |
| `api_keys` | SHA-256 hash, prefix, created and revoked times |
| `runs` | One agent run: source (recorded, replay), parent run, start step, status |
| `steps` | One row per step: model output, tool calls, tool results, message snapshot |
| `replay_jobs` | Queue: run, save point, fixed step, lease, status, result run |
| `diagnoses` | One per diagnose request: status, first domino step, verified, cost |
| `checks` | One per bisect or verify check: save point, passes, total |
| `causes` | Grouped root causes: title, category, explanation, suggested fix |
| `benchmark_results` | Method, run, predicted step, true step, cost |

## Auth

- People sign in to the web app with Google through NextAuth. The web app's server mints a short-lived HS256 token with a secret shared with `fd-api`, which verifies it and finds or creates the person.
- The SDK and worker send a project API key in the `Authorization: Bearer` header.

## Contract

`docs/CONTRACT.md` is the agreement; `fd-api` implements it. `make openapi` writes `server/api/openapi.json`. `make sdk-models` generates the SDK models from it, and the web app generates its TypeScript client and Zod schemas from the same file.
