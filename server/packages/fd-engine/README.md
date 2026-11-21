# fd-engine

The core: search over save points, verify by replay, fall back to nearby steps, then explain and group. It never touches the database or HTTP; it works through the ports the API implements, and is tested on fakes with no network.

- **Layer:** Logic (the core)
- **May import:** `fd-shared`
- **Must never import:** `fd-database`, `fd-api`, `first-domino`
- **Rules:** [`.claude/rules/engine.md`](../../.claude/rules/engine.md)

## Modules

| Module | Job |
| --- | --- |
| `settings` | `EngineSettings`: samples per check, doomed rechecks, verify threshold, fallback window, model ids and timeouts. |
| `ports` | The ports the engine depends on: `ReplayRunner`, `RunReader`, `CheckSink` and `CostSink`. |
| `errors` | Errors that stop a diagnosis, each with a stable `code`. |
| `checks` | Runs one check: replay from a save point, count passes, report it. |
| `bisect` | Binary search for the first step from which the run is doomed; a check with no pass is rechecked. |
| `verify` | Rewrite the found step and replay to prove it flips the outcome. |
| `fallback` | Try nearby steps when verify does not prove the found one. |
| `fix` | Asks the model for a corrected version of a step. |
| `explain` | Plain-language cause, category and suggested fix. |
| `group` | Files a cause under a matching root cause or starts a new one. |
| `diagnose` | Runs one diagnosis end to end. |
| `transcript` | Renders a run's steps as text for the model prompts. |
| `llm` | The backend's only OpenAI client: structured calls with retries. |
