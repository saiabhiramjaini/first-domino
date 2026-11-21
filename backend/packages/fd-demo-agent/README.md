# fd-demo-agent

The demo customer: a booking agent with mock tools, a success check and a replay worker, using only the public SDK.

- **Layer:** Demo customer
- **May import:** `first-domino` and third-party libraries
- **Must never import:** any `fd-*` package
- **Rules:** [`.claude/rules/demo-agent.md`](../../.claude/rules/demo-agent.md)

## Modules

| Module | Job |
| --- | --- |
| `settings` | DemoAgentSettings: agent model, maximum steps and the fixed today. |
| `agent` | The agent loop: one model turn plus its tool results per step. |
| `tools` | Mock tools: pure functions over the world data and a per-run booking sandbox. |
| `world/` | Loads the mock world data into typed models. |
| `tasks` | Demo tasks and their expected outcomes. |
| `success` | Success check: compare the final booking with the expected booking. |
| `bugs` | Planted bug definitions used to build the benchmark dataset. |
| `worker` | Entry point for the demo customer's replay worker. |

Status: layout only. Modules hold a docstring that states their job; no code yet.
