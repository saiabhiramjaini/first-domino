# Brief S2: customer side (demo agent and SDK)

You are the customer-side engineer for **First Domino**. First Domino finds the step where a failed AI agent run became doomed: it re-runs the agent from its own save points, binary-searches for the first doomed step, then proves it by fixing that step and replaying. You build two things: the demo agent that plays a real customer, and the public SDK (`pip install first-domino`) that customers use to record runs and run replays.

**Open this chat in `server/`** (inside your worktree), so it loads the backend rules, hooks and skills. Paths below are from the repo root.

## Read first, in this order

1. `AGENTS.md` (repo-wide rules), then `server/AGENTS.md` (Python rules)
2. `docs/PARALLEL_WORK.md`
3. `docs/CONTRACT.md` (especially "Worker protocol" and "SDK public surface")
4. `docs/ARCHITECTURE.md`
5. `server/.claude/rules/demo-agent.md`, `server/.claude/rules/sdk.md`
6. `server/REVIEW.md`

## You own

`server/packages/fd-demo-agent/`, `server/packages/first-domino/` (except `_generated/`, which S0 regenerates) and `docs/status/s2.md`. Never import an `fd-*` package from either.

## The demo domain

The demo agent is a generic AI call assistant: it answers incoming phone calls on the user's behalf, talks to the caller, then takes the actions the call needs, using what it knows about the user. Calls are text transcripts; there is no audio. The user is **Arjun Rao** in Hyderabad. Fixed "today" is Saturday 21 Nov 2026, 11:00 AM IST.

The customer workspace in demo data is named **"Call assistant (demo)"**. No real companies or people: the user, callers and businesses are fictional. In code the agent is `call-assistant`.

## Tasks, in order

### 1. Mock world (no backend needed)

- `world/data/*.json`, loaded into Pydantic models through `importlib.resources`:
  - **contacts**: about 25 saved contacts with phone numbers and relationships, including near-duplicate Indian names (Dr. Mehta's clinic and Mehta Electricals; Lakshmi and Laxmi Narayana; Srinivas and Srinivasa Rao).
  - **memory**: the user's personal context, such as "Dr. Mehta's clinic is my family doctor", "remind me 1 hour before any appointment", "always carry previous medical reports to the doctor", "never share OTPs or bank details", "home address: ...".
  - **calendar**: the user's existing events for the next 7 days.
  - **known spam numbers**.
- Tools as pure functions over a per-run sandbox: `lookup_contact(phone)`, `search_memory(query)`, `check_calendar(date)`, `reply_to_caller(text)`, `add_calendar_event(title, date, time, notes)`, `move_calendar_event(event_id, date, time)`, `set_reminder(event_id, minutes_before)`, `schedule_callback(contact, date, time, reason)`, `block_caller(phone, reason)`, `send_call_summary(summary, action_items)`, `end_call()`.
- **The caller is scripted, so replays are deterministic.** Each call has a fixed list of caller lines. `reply_to_caller` records what the assistant said and returns the caller's next line (or `[caller hung up]`), chosen by turn number, never by what the assistant said.

### 2. Agent loop and success check (milestone C2)

- `agent.py`: our own loop over the OpenAI SDK, one step per model turn plus its tool results, a save point after every step, able to start from any message list, honour a replacement output for the next step, and run with a model override. Keep the existing loop, sandbox rebuild, runner and bug-planting mechanism; only the world, tools, prompts, tasks, success check and bugs change.
- `tasks.py`: 10 incoming calls, each with the caller's number, the scripted caller lines and the expected end state. Cover: a clinic confirming an appointment "tomorrow at 10" (calendar event, reminder 1 hour before, note to carry reports); a bank loan offer (block, no callback); an OTP scam (refuse, block, warn in the summary); a delivery rider asking for directions (share the saved address); a plumber moving a visit "to the day after tomorrow, evening" (move the event); a school parent-teacher meeting "this Friday at 4" (event and reminder); a friend asking to call back after 6 (callback); a landlord rent reminder (reminder); a caller mixing Hindi and English; a caller whose name is close to another contact.
- `success.py`: plain-code check of the final sandbox against the task's expected end state: events (title, date, time, notes), reminders, callbacks, blocked numbers, required facts in the summary, and nothing sensitive said to the caller.
- `bugs.py`: 8 planted bug types as data, each naming the step to overwrite and the replacement output: "tomorrow" resolved to the day after, 10 AM booked as 10 PM, the wrong contact picked from near-duplicate names, the "carry reports" instruction dropped from the notes, the reminder set 1 day before instead of 1 hour, a spam call treated as genuine (callback instead of block), an OTP read out to a scam caller, the callback set for the wrong person.
- Run the agent locally and show completed and failed calls with their steps.

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
