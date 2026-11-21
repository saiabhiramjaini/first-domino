# fd-api

FastAPI control plane: auth, run ingest, the replay job queue, diagnoses and root causes. It runs the engine for each diagnosis as a tracked background task.

- **Layer:** Service
- **May import:** `fd-shared`, `fd-database`, `fd-engine`
- **Must never import:** `first-domino`
- **Rules:** [`.claude/rules/api.md`](../../.claude/rules/api.md)

## Modules

| Module | Job |
| --- | --- |
| `main` | Application factory: routers, error handlers, startup and shutdown. |
| `settings` | `ApiSettings`: web token secret, allowed origins, job leases, diagnosis heartbeat and restart window, list limits. |
| `database` | The request's database session: one transaction per request. |
| `errors` | Maps typed errors to stable HTTP error responses. |
| `pagination` | Page request and response bases, and the count response. |
| `auth/` | Who is calling: web session tokens for people (`users`), project API keys for the SDK (`api_keys`), and the shared caller type. |
| `models/` | Request and response models, one module per resource. |
| `routers/` | One router per resource: projects, API keys, runs, steps, diagnoses, checks, causes, replay jobs and health. |
| `services/diagnoses` | Creating a diagnosis, for `createDiagnosis` and auto-diagnosis. |
| `services/diagnosis_runner` | Runs diagnoses as tracked background tasks, heartbeats them, and restarts or fails ones whose process stopped. |
| `services/engine` | Builds the engine for one diagnosis over the adapters. |
| `services/verdicts` | Stores the verdict and files it under a root cause. |
| `services/exports` | Turns a cause's runs into regression test cases. |
| `services/snapshots` | The message list at a save point of a recorded run. |
| `services/slack` | Posts a new root cause to a project's Slack webhook, when one is set. |
| `adapters/` | The engine ports: `replay_runner` over the job queue, `run_reader` over runs and steps, `check_sink` and `check_tracker` for live checks. |
| `export_openapi` | Writes `api/openapi.json` (`make openapi`). |
| `dev_api_key` | A local API key without the web app (`make dev-key`). |
| `seed_demo` | Prepares the demo workspace (`make seed-demo EMAIL=...`). |
