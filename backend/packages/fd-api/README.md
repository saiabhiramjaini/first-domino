# fd-api

FastAPI control plane: auth, run ingest, the replay job queue, diagnoses, causes and the benchmark.

- **Layer:** Service
- **May import:** `fd-shared`, `fd-database`, `fd-engine`
- **Must never import:** `first-domino`, `fd-demo-agent`
- **Rules:** [`.claude/rules/api.md`](../../.claude/rules/api.md)

## Modules

| Module | Job |
| --- | --- |
| `main` | Application factory: routers, error handlers, startup and shutdown. |
| `settings` | ApiSettings: Clerk issuer, allowed origins, job lease time and list limits. |
| `errors` | Maps typed errors to stable HTTP error responses. |
| `auth/` | Authentication dependencies. |
| `auth/users` | Clerk session verification for people using the web app. |
| `auth/api_keys` | Project API key verification for the SDK and the worker. |
| `routers/` | One router per resource. |
| `routers/projects` | Projects routes. |
| `routers/api_keys` | API keys routes: create, list and revoke. |
| `routers/runs` | Runs routes: list, get, start and finish a recorded run. |
| `routers/steps` | Steps routes: record a step and list the steps of a run. |
| `routers/diagnoses` | Diagnoses routes: start a diagnosis and read its checks and verdict. |
| `routers/causes` | Causes routes: list cause groups and get one with its runs. |
| `routers/replay_jobs` | Worker protocol routes: lease a replay job and submit its result. |
| `routers/benchmark` | Benchmark routes: start a benchmark and read the latest scores. |
| `services/` | Application services that coordinate the engine and storage. |
| `services/diagnosis_runner` | Registry that runs diagnoses as tracked background tasks. |
| `adapters/` | Adapters that implement the engine ports. |
| `adapters/replay_runner` | ReplayRunner port over the replay job queue. |
| `adapters/run_reader` | RunReader port over the runs and steps repositories. |
| `adapters/check_sink` | CheckSink port that stores each check for the web app. |

Status: layout only. Modules hold a docstring that states their job; no code yet.
