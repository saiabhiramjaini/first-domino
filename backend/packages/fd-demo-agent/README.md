# fd-demo-agent

The demo customer: an AI call assistant with mock tools, scripted callers, a success check and a replay worker, using only the public SDK. Its SDK agent name is `call-assistant`.

It is our own replica of the kind of AI call assistant Equal AI describes publicly: it answers calls for the user, does the work, then sends a summary and adds callbacks, calendar events and reminders, using the user's personal context. Equal AI is not involved and does not use or endorse First Domino.

- **Layer:** Demo customer
- **May import:** `first-domino` and third-party libraries
- **Must never import:** any `fd-*` package
- **Rules:** [`.claude/rules/demo-agent.md`](../../.claude/rules/demo-agent.md)

## Modules

| Module | Job |
| --- | --- |
| `settings` | DemoAgentSettings: agent model, step limit and the OpenAI key. |
| `world/` | Loads the mock world JSON (the user and fixed now, contacts, memory, calendar, spam numbers) into typed models. |
| `tools` | Mock tools as pure functions over the world and the call sandbox. |
| `sandbox` | The per-call sandbox: the scripted caller and every event, reminder, callback, block and summary the run makes. |
| `toolbox` | Tool definitions for OpenAI and dispatch of a tool call to its function. |
| `messages` | Helpers over OpenAI message params, the agent's conversation format. |
| `prompts` | The system prompt and a call's opening messages. |
| `llm` | The `ChatModel` port and its OpenAI implementation. |
| `agent` | The agent loop: one model turn plus its tool results per step; runs from any save point. |
| `tasks` | The 10 demo calls: number, scripted caller lines and expected end state. |
| `expected` | Models of the expected end state. |
| `success` | Success check: compare the final sandbox with the expected end state. Plain code. |
| `bugs` | Eight planted bugs as data: call, step to overwrite, replacement output. |
| `runner` | Run one call, optionally with a planted bug, and check the result. |
| `recording` | Record runs through the public SDK: task input with ids, steps, verdict. |
| `local` | Command line to run calls against OpenAI, log every step and record them. |
| `worker` | The demo customer's replay worker: replays the agent and runs the success check. |

## Run locally

Needs `OPENAI_API_KEY` and `FD_DEMO_AGENT_MODEL` in `backend/.env`. From `backend/`:

```bash
uv run python -m fd_demo_agent.local --task t01
uv run python -m fd_demo_agent.local --bug b01
uv run python -m fd_demo_agent.local --all
```

With `FIRST_DOMINO_API_KEY` and `FIRST_DOMINO_BASE_URL` also set, each run is recorded to First Domino as `call-assistant`, with `task_id` (and for a planted bug, `bug_id` and `planted_step`) in its metadata. `make worker` starts the replay worker.

The user is Arjun Rao in Hyderabad, and now is fixed at Saturday 21 Nov 2026, 11:00 AM IST. The caller is scripted: `reply_to_caller` returns the call's next line by turn number, so replays hear the same caller. Every person, caller and business is fictional.
