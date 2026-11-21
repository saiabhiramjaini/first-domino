# fd-engine

The core: bisect over save points, verify by replay, fallback, explain, group and the baseline judge.

- **Layer:** Logic (the core)
- **May import:** `fd-shared`
- **Must never import:** `fd-database`, `fd-api`, `first-domino`
- **Rules:** [`.claude/rules/engine.md`](../../.claude/rules/engine.md)

## Modules

| Module | Job |
| --- | --- |
| `settings` | EngineSettings: samples per check, verify threshold, fallback window, model ids and timeouts. |
| `ports` | Protocol ports the engine depends on: ReplayRunner, RunReader and CheckSink. |
| `errors` | Errors that stop a diagnosis, each with a stable `code`. |
| `checks` | Runs one check: replay from a save point, count passes, report it through the sink. |
| `diagnose` | Runs one diagnosis end to end: bisect, verify or fallback, explain and group. |
| `bisect` | Binary search over save points for the first step from which the run is doomed. |
| `verify` | Rewrite the found step and replay to prove that it flips the outcome. |
| `fallback` | Rank and try nearby suspect steps when verify does not prove the found step. |
| `fix` | Asks the model for a corrected turn of the suspected step (the `StepFixer` verify uses). |
| `transcript` | Renders a run's steps as text for the model prompts. |
| `explain` | Plain-language cause, category and suggested fix for a verified step. |
| `group` | Attach a cause to a matching cause group or start a new one. |
| `baseline` | Read-the-trace baseline judge, used only by the benchmark. |
| `llm` | The only OpenAI client in the backend: structured calls with retry, salvage and degrade. |

Status: ports, settings, bisect, verify, fallback, diagnose, fix, explain, group and baseline done and tested on fakes (no network). Next: run against the real API through S0's adapters and tune.
