---
paths:
  - "packages/fd-demo-agent/**"
---

# fd-demo-agent rules

The demo agent plays a real customer. It uses only what a customer would have.

- Import only `first-domino` and third-party libraries. Never import an `fd-*` package.
- The agent loop is our own small loop over the OpenAI SDK, not an agent framework, so every step and message snapshot is under our control.
- One step is one model turn plus the results of the tools it called.
- Mock tools are pure functions of their arguments and a fixed "today" (Sat 21 Nov 2026). Same input, same output, every time. Bookings write to a per-run sandbox, never to shared state.
- World data (contacts, the user's memory, the calendar, spam numbers) lives in `fd_demo_agent/world/data/` as JSON, is read with `importlib.resources`, and is loaded into Pydantic models.
- The caller is scripted: `reply_to_caller` returns the next fixed line by turn number, never by what the assistant said.
- The success check is plain code that compares the final sandbox (events, reminders, callbacks, blocked numbers, summary facts, nothing sensitive said) with the task's expected end state. No model call.
- The agent replicates Equal AI's call assistant, our first customer. Only the demo workspace label "Equal AI (demo)" uses their name: no logos, no claim of endorsement, no real people. Callers and businesses are fictional.
- Planted bugs for the benchmark are defined as data (task id, step to overwrite, replacement output), never as branches in the agent loop.
- The agent model id comes from `DemoAgentSettings`. Never hardcode it.
