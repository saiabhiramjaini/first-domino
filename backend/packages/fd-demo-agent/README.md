# fd-demo-agent

The demo customer: a booking agent with mock tools, a success check and a replay worker, using only the public SDK.

- **Layer:** Demo customer
- **May import:** `first-domino` and third-party libraries
- **Must never import:** any `fd-*` package
- **Rules:** [`.claude/rules/demo-agent.md`](../../.claude/rules/demo-agent.md)

## Modules

| Module | Job |
| --- | --- |
| `settings` | DemoAgentSettings: agent model, step limit and the OpenAI key. |
| `world/` | Loads the mock world JSON (clinics, doctors, slot statuses, the fixed today) into typed models. |
| `tools` | Mock tools as pure functions: `search_doctors`, `list_slots`, `check_fee`, `book_appointment`. |
| `sandbox` | The per-run booking sandbox. A run may make one appointment request and cannot cancel it. |
| `toolbox` | Tool definitions for OpenAI and dispatch of a tool call to its function. |
| `messages` | Helpers over OpenAI message params, the agent's conversation format. |
| `prompts` | The system prompt and a task's opening messages. |
| `llm` | The `ChatModel` port and its OpenAI implementation. |
| `agent` | The agent loop: one model turn plus its tool results per step; runs from any save point. |
| `tasks` | Ten demo tasks and their expected bookings. |
| `success` | Success check: compare the final booking with the expected booking. Plain code. |
| `bugs` | Eight planted bugs as data: task, step to overwrite, replacement output. |
| `runner` | Run one task, optionally with a planted bug, and check the result. |
| `local` | Command line to run tasks against OpenAI and log every step. |
| `worker` | Entry point for the demo customer's replay worker (after the SDK lands). |

## Run locally

Needs `OPENAI_API_KEY` and `FD_DEMO_AGENT_MODEL` in `backend/.env`. From `backend/`:

```bash
uv run python -m fd_demo_agent.local --task t01
uv run python -m fd_demo_agent.local --bug b02
uv run python -m fd_demo_agent.local --all
```

Today is fixed at Saturday 21 Nov 2026. Clinic and doctor names are fictional.
