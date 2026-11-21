# Brief S2: customer side (demo agent and SDK)

You are the customer-side engineer for **First Domino**, a hackathon project (Builders 2026, code freeze Sunday 22 Nov 2026 at 2:00 PM). First Domino finds the step where a failed AI agent run became doomed: it re-runs the agent from its own save points, binary-searches for the first doomed step, then proves it by fixing that step and replaying. You build two things: the demo agent that plays a real customer, and the public SDK (`pip install first-domino`) that customers use to record runs and run replays.

**Open this chat in `backend/`** (inside your worktree), so it loads the backend rules, hooks and skills. Paths below are from the repo root.

## Read first, in this order

1. `AGENTS.md` (repo-wide rules), then `backend/AGENTS.md` (Python rules)
2. `docs/PARALLEL_WORK.md`
3. `docs/CONTRACT.md` (especially "Worker protocol" and "SDK public surface")
4. `docs/ARCHITECTURE.md`
5. `backend/.claude/rules/demo-agent.md`, `backend/.claude/rules/sdk.md`
6. `backend/REVIEW.md`

## You own

`backend/packages/fd-demo-agent/`, `backend/packages/first-domino/` (except `_generated/`, which S0 regenerates) and `docs/status/s2.md`. Never import an `fd-*` package from either.

## The demo domain

A **doctor appointment booking agent** for Indian clinics, in the spirit of an AI assistant that books on your behalf. Fixed "today" is Saturday 21 Nov 2026. Example request: "Book Dr. Mehta at Apollo Kukatpally for tomorrow morning, under ₹800, for my father Ramesh."

## Tasks, in order

### 1. Mock world (no backend needed)

- `world/data/*.json`: about 6 clinics in Hyderabad and Bengaluru, 15 doctors with specialities and fees, slots for the next 7 days with availability.
- Pydantic models and loading through `importlib.resources`.
- Tools as pure functions: `search_doctors`, `list_slots`, `check_fee`, `book_appointment` (writes to a per-run sandbox).

### 2. Agent loop and success check (milestone C2)

- `agent.py`: our own loop over the OpenAI SDK, one step per model turn plus its tool results, a save point after every step, able to start from any message list, honour a replacement output for the next step, and run with a model override.
- `tasks.py`: 10 tasks covering date words ("tomorrow", "this Friday", "26th"), time windows, fee limits, specialities and Indian names (Ramesh, Akhilesh, Lakshmi).
- `success.py`: plain-code check of the final booking against the task's expected booking.
- `bugs.py`: 8 planted bug types as data (wrong date, wrong clinic branch, wrong time window, fee checked against the wrong fee, swapped arguments, invented doctor, waitlist treated as booked, misspelled patient name), each naming the step to overwrite and the replacement output.
- Run the agent locally and show completed and failed runs with their steps.

### 3. SDK (after contract v1)

- `client.py` over `httpx` with the generated models; `settings.py` with the `FIRST_DOMINO_` prefix.
- `recorder.py` (`record`, `run.step`, `run.finish`) and `wrap.py` (OpenAI client wrapper): no-ops without an API key, and never raise into the agent.
- `worker.py`: the lease, run, check, submit loop exactly as the contract's worker protocol says.
- `diagnose.py`; `cli.py` only if time allows.
- A README written for customers: install, record, worker, diagnose.

### 4. Wire the demo agent to the SDK (milestone C3)

- The demo agent records through the SDK.
- `fd_demo_agent/worker.py` starts an SDK worker that replays the demo agent and runs `success.py`.
- Against the running API: a planted-bug run is recorded, diagnosed and replayed end to end.

## Rules that matter most here

- The SDK depends only on `httpx`, `pydantic`, `pydantic-settings`, and optionally `openai`.
- Mock tools are deterministic: same input, same output.
- `make check` passes before you call anything done.

## Report

Keep `docs/status/s2.md` current in the shape `docs/PARALLEL_WORK.md` gives. Put SDK needs from the API under "Contract requests".
