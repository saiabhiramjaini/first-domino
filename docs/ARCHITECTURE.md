# Architecture

## The idea in one paragraph

An agent run is a list of steps. Each step is one model call plus the results of the tools it asked for, so every step is a save point. To diagnose a failed run, the engine asks: "if we keep steps 1 to m exactly as recorded and let the agent run the rest, can it still succeed?" It binary-searches m for the first save point from which the run always fails. That step is the first domino. The engine then rewrites that one step and replays to prove the fix turns the failure into a pass.

## Components

```
 Browser ──► web app (Next.js, Vercel) ──► fd-api (EC2) ──► Postgres (Neon)
                                              │  ▲
                                 runs engine  │  │ checks, verdicts
                                              ▼  │
                                          fd-engine
 Customer side
 ──────────────────────────────────────────────────────────────────────────
 customer agent + first-domino SDK
   @fd.entrypoint ── records runs and steps live ─────────► fd-api
   fd.serve()     ◄── leases replay jobs ───────────────── fd-api
                  └── submits replay outcomes ─────────────► fd-api
```

| Component | Runs where | Job |
| --- | --- | --- |
| `fd-api` | our cloud (EC2, Docker) | Auth, ingest, the replay job queue, diagnoses, root causes |
| `fd-engine` | inside `fd-api` | Picks which save point to test, reads the outcomes, proves and explains the cause |
| `fd-database` | our cloud (Neon Postgres) | Tables and repositories |
| `first-domino` SDK | customer side | Records runs; the replay worker runs the customer's agent on request |
| `client/` | our cloud (Vercel) | Runs, run traces with the verdict, root causes, settings |

## Why replays run on the customer side

The agent needs its own code, secrets, tools and data. Running it on our side would mean taking all of that. Instead the SDK's worker runs next to the agent, leases replay jobs from the API and submits the outcomes. It only connects outward, so the customer exposes no endpoint. This is the model of Temporal workers and self-hosted CI runners.

## How the SDK records any agent

`@fd.entrypoint` marks the function that runs the agent; each call becomes one run. The SDK patches `send` on the `httpx` and `httpx2` clients that the OpenAI and Anthropic SDKs use, so every model request made inside that function is seen, whatever framework makes it:

- OpenAI Chat Completions (and the APIs compatible with it), OpenAI Responses and Anthropic Messages, plain or streamed.
- A model call becomes a step once the next request carries its tool results (or the run ends).
- Steps are sent from a background thread in order, so recording never blocks or breaks the agent. Without an API key nothing is recorded.

During a replay, `fd.serve()` calls the same function again. Model calls up to the save point are answered from the recording, the next one with the fixed step when the job has one, and the rest by the live model. Tools marked `@fd.tool` return their recorded results inside the recorded part, so side effects are not repeated and results that change over time stay as recorded. Unmarked tools run live; if one returns something different from the recording, the replay reports drift (see below). The lower-level `fd.record`, `fd.wrap` and `fd.Worker` remain for full control.

## Flows

### 1. Record a run

1. The agent runs inside `@fd.entrypoint` (or `fd.record`).
2. The run appears in the web app at once; each step is sent as it completes: model output, tool calls, tool results and the message snapshot.
3. When the function returns, the customer's check (or `fd.set_outcome`, which can also say why) marks the run passed or failed. A run that raises is errored.
4. Failures no check catches are flagged later (`fd.flag`, or Mark as failed in the web app) with what went wrong. The run becomes failed and is diagnosed.

### 2. Diagnose a failed run

1. A failed recorded run is diagnosed automatically, or from the run page.
2. `fd-api` creates a diagnosis and runs the engine as a tracked background task.
3. The engine calls the `ReplayRunner` port: "replay run R from save point m, k times".
4. The API adapter turns that into replay jobs in Postgres and waits for their outcomes.
5. The worker leases the jobs, replays, runs the customer's check and submits the outcomes.
6. The engine narrows the search range and asks for the next check, until one step is left.
7. Verify: the engine asks a model to rewrite that step, then replays from the fixed step.
8. Explain and group: the engine writes what went wrong and files it under a matching root cause. A cause seen for the first time emails the project owner: fd-api asks the web app to send the mail.
9. Every check is stored as it runs, so the web app shows the search live.

### Replay job lifecycle

```
queued ──► leased ──► succeeded | failed
   ▲          │
   └──────────┘  lease expired (worker died): back to queued, then expired after the last attempt

queued | leased ──► expired   the check was decided without it
```

- A worker leases a job for a fixed time. An expired lease returns it to the queue.
- An outcome is idempotent by job id: a repeated submit does not count twice.
- A check stops as soon as its result is known. Its other jobs are ended; the worker skips queued ones and stops running ones at their next model call, so no model calls are spent on outcomes nobody reads.
- When no worker has picked a diagnosis's jobs up, the web app says it is waiting for the replay worker.
- A replay run left `running` by a worker that died or was stopped is ended as `errored` a few minutes after its job moved on.

## The search and the proof

- Calibrate first: keep every step (m = n) and replay a couple of times. Every model call is answered from the recording, so it costs no model tokens. The success check must fail these replays; if it passes one, the check (or the world it reads) does not reliably fail this run, and the diagnosis stops as `check_inconsistent` instead of blaming a step.
- `can_succeed(m)`: keep steps 1..m and replay the rest k times. True if any replay passes.
- A check with no pass is run once more before the save point counts as doomed, since a few unlucky replays look the same as a doomed one.
- If a fresh run (m = 0) never passes, the verdict is a task or tool issue, not an agent step.
- Invariant: the run can succeed from `lo - 1` and is doomed at `hi` (calibration checked it at `n`). Halve until `lo == hi`.
- For a flagged run, the customer's check passed the original, so it cannot judge replays. The engine judges each replay instead: a model reads the replay's recorded transcript and final output against the reported failure. Calibration then also checks the judge: it must call the unchanged replay a failure before any step is blamed.
- The failure reason, when there is one, goes into the fixer's and explainer's prompts.
- Only faithful replays are evidence. While a replay is inside the kept steps, the SDK compares each tool result with the recorded one; on a difference the replay has drifted (a tool read live data, the clock or randomness), stops at its next model call and is reported with the step and tool. Drifted replays count toward neither samples nor passes. A check left with no evidence because its replays drifted stops the diagnosis as `replay_not_faithful`, naming the tool to mark with `@fd.tool`.
- Verify: rewrite step `lo` and replay. It is proven when enough replays pass.
- If verify fails, the nearby steps are tried in turn. If none flips the outcome, the verdict is "multiple causes".

Sample counts, the verify threshold, the recheck size and the fallback window are engine settings (`FD_ENGINE_*`).

## Restarts

Diagnoses run inside the API process and heartbeat while they run. When the API stops, it hands its unfinished diagnoses back; the next API process (or a live one, at its next heartbeat) restarts recent ones from the beginning and expires their old replay jobs. A diagnosis older than `FD_API_DIAGNOSIS_RESTART_WITHIN_SECONDS` is failed as interrupted instead, so one that keeps crashing the API cannot loop.

## Data model

| Table | Holds |
| --- | --- |
| `users` | People who signed in with Google |
| `projects` | The tenant boundary; every other table carries `project_id` |
| `api_keys` | SHA-256 hash, prefix, last use, revoked time |
| `runs` | One agent run: source (recorded or replay), parent run, status, task input, tool names, failure reason, who flagged it |
| `steps` | One row per step: model output, tool results, message snapshot, tokens, latency |
| `replay_jobs` | The queue: run, save point, fixed step, model override, lease, attempt, outcome, drift |
| `diagnoses` | One per diagnosis: status, verdict, first domino, proof, explanation, cost, owner heartbeat |
| `checks` | One per check: phase, save point, samples, passes, result, drifted replays and the drifting tool |
| `causes` | Root causes: title, category, step name, suggested fix, run counts |

## Auth

- People sign in to the web app with Google through NextAuth. The web server mints a short-lived HS256 token with a secret shared with `fd-api`, which verifies it and finds or creates the person and their project.
- The SDK and the worker send a project API key (`fd_live_...`) as a bearer token.

## Contract

`docs/CONTRACT.md` is the agreement; `fd-api` implements it. `make openapi` writes `server/api/openapi.json`, `make sdk-models` generates the SDK's wire models from it, and the web app generates its TypeScript client and Zod schemas from the same file.
