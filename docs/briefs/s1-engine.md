# Brief S1: the engine

You are the engine engineer for **First Domino**. First Domino finds the step where a failed AI agent run became doomed: it re-runs the agent from its own save points, binary-searches for the first doomed step, then proves it by fixing that step and replaying. The engine is the core of the product and the part judges will ask about. It decides; it never does I/O except model calls.

**Open this chat in `server/`** (inside your worktree), so it loads the backend rules, hooks and skills. Paths below are from the repo root.

## Read first, in this order

1. `AGENTS.md` (repo-wide rules), then `server/AGENTS.md` (Python rules)
2. `docs/PARALLEL_WORK.md`
3. `docs/ARCHITECTURE.md` (especially "The bisect rule")
4. `docs/CONTRACT.md` (especially "Engine ports")
5. `server/.claude/rules/engine.md`
6. `server/REVIEW.md`

## You own

`server/packages/fd-engine/` and `docs/status/s1.md`. Never edit another package. If you need a model or enum in `fd-shared`, write the request in your status file; until S0 adds it, define a local model in `fd_engine` and switch later.

## Tasks, in order

### 1. Ports first (needed by S0 for milestone C1)

Write `fd_engine/ports.py` exactly as the contract describes: `RunReader`, `ReplayRunner`, `CheckSink` as `typing.Protocol` classes. Commit this first and tell the user, because S0 builds the adapters against it.

### 2. Settings

`EngineSettings` (`FD_ENGINE_` prefix): samples per check, verify samples and pass threshold, fallback window, maximum checks, replay timeout, strong model id, the OpenAI key through an alias, per-call timeouts. No inline numbers anywhere else.

### 3. Bisect and verify (milestone C2)

- `bisect.py`: precheck at save point 0, then the binary search with the invariant "can succeed at `lo - 1`, doomed at `hi`". Report every check through `CheckSink`.
- `verify.py`: ask the model for a corrected output for the found step, replay from it with the agent's own model, compare passes with the threshold.
- `fallback.py`: when verify fails, rank nearby steps and try a fix on each; report `multiple_causes` when none flips the outcome.
- `diagnose.py`: the orchestration that returns `DiagnosisResult`, including counts and cost.
- Unit tests with a fake `ReplayRunner` that returns scripted outcomes per save point: a clean break, a break at step 1, a task that always fails, a flaky middle, a verify that does not flip. No network, no database.

### 4. Model calls

- `llm.py`: the only OpenAI client in the backend. Structured output parsed into Pydantic models; retry once, salvage, degrade. Records tokens and cost.
- `explain.py`: title, summary, category and suggested fix for a verified step.
- `group.py`: match a new explanation to an existing cause or start a new one (given the current causes as input; storage is S0's).
- `baseline.py`: the read-the-trace judge used by the benchmark: whole trace in, predicted step out.

### 5. Hardening (before C4)

Run the engine against the real API through S0's adapters. Tune samples and prompts so a clean planted bug is found in the fewest replays.

## Rules that matter most here

- No imports of `fd-database`, `fd-api`, `httpx` or `first-domino`. Everything external comes through the ports.
- A verdict is verified only when passes meet the configured threshold. Never round partial results up.
- `make check` passes before you call anything done.

## Report

Keep `docs/status/s1.md` current in the shape `docs/PARALLEL_WORK.md` gives.
