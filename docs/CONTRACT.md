# Contract

**Contract version: 1 (implemented with example data; real handlers land resource by resource without changing it)**

This is the one agreement every workstream builds against: the HTTP API, the worker protocol, the engine ports and the SDK's public surface. The API code is the source of truth once it exists; until then, this file is. `api/openapi.json` is generated from the API and must match this file.

Only the platform backend workstream (S0) edits this file. Anyone else who needs a change writes it under "Contract requests" in their `docs/status/<stream>.md`. S0 applies it, bumps the version above, regenerates `api/openapi.json` and the SDK models, and merges. Everyone else pulls and regenerates their client.

## Conventions

- Base URL: `FIRST_DOMINO_BASE_URL` (local `http://localhost:8000`). All routes are under `/v1`.
- Paths are dot actions: `/v1/<resource>.<action>`. Reads with an id use `GET` with query parameters; everything else uses `POST` with a JSON body.
- `operation_id` is camelCase, verb first. Request and response models are `<OperationId>Request` and `<OperationId>Response`.
- A single object comes back in an envelope with one field named for it (`{"run": {...}}`).
- Ids we mint are UUIDs. Timestamps are UTC RFC 3339 strings. Money is `cost_usd` as a number with up to 6 decimals.
- Every list is a page. Request: `limit` (1 to 100, default 50) and `cursor` (opaque string or null). Response: `items` and `next_cursor` (null on the last page).
- Field names are snake_case on the wire.
- `GET` operations take their request fields as query parameters (`GET /v1/runs.get?run_id=...`).
- Until real auth lands, any bearer token is accepted: one starting `fd_live_` acts as an API key, anything else as a person, both in one example project.

## Auth

| Caller | How | Used by |
| --- | --- | --- |
| Person | `Authorization: Bearer <web session token>` | Web app |
| SDK or worker | `Authorization: Bearer <project API key>` (`fd_live_` prefix) | `first-domino` SDK, demo agent |

- People sign in to the web app with Google through NextAuth (Auth.js v5, JWT sessions, no database adapter). The web app's server mints the **web session token**: an HS256 JWT signed with the secret both halves share (`API_JWT_SECRET` in the frontend, `FD_API_WEB_JWT_SECRET` in the backend), with claims `sub` (the Google account id), `email`, `name`, `iss` = `first-domino-web`, `aud` = `first-domino-api`, `iat` and `exp` (1 hour). It is re-minted before it expires.
- The API verifies the signature, issuer, audience and expiry, then finds or creates the person by `sub`. It never trusts other claims for access.
- A person's first authenticated call creates their project. A person has exactly one project during the hackathon.
- Each operation below lists which caller it accepts: **P** (person), **K** (API key) or **P/K**.

## Errors

Every error body is `{"code": ..., "title": ..., "detail": ...}`. `code` is stable; branch on it, never on `title` or `detail`.

| Status | `code` | When |
| --- | --- | --- |
| 400 | `bad_request` | The body is not valid JSON |
| 401 | `unauthenticated` | Missing, expired or revoked token or key |
| 403 | `permission_denied` | The project has the object but this caller may not use it |
| 404 | `not_found` | The project does not have the object (including another project's) |
| 409 | `conflict` | State does not allow the action (finishing a finished run, a second diagnosis while one runs) |
| 422 | `validation_failed` | Field errors; the body adds `errors: [{field, message}]` |
| 500 | `internal_error` | Unexpected; the body adds `request_id` |

## Enums

| Enum | Values |
| --- | --- |
| `RunStatus` | `running`, `passed`, `failed`, `errored` |
| `RunOutcome` | `passed`, `failed`, `errored` (how `finishRun` ends a run) |
| `RunSource` | `recorded`, `replay` |
| `MessageRole` | `system`, `user`, `assistant`, `tool` |
| `DiagnosisStatus` | `queued`, `bisecting`, `verifying`, `explaining`, `done`, `failed` |
| `VerdictKind` | `step_verified`, `step_unverified`, `multiple_causes`, `task_or_tool_issue` |
| `CheckPhase` | `precheck`, `bisect`, `verify`, `fallback` |
| `CheckResult` | `pending`, `can_succeed`, `doomed` |
| `ReplayJobStatus` | `queued`, `leased`, `succeeded`, `failed`, `expired` |
| `ReplayOutcome` | `passed`, `failed`, `errored` |
| `CauseCategory` | `wrong_date`, `wrong_entity`, `wrong_filter`, `bad_tool_args`, `hallucination`, `tool_issue`, `other` |
| `BenchmarkMethod` | `first_domino`, `read_trace_judge` |
| `ApiErrorCode` | the `code` values in the table above |

## Shared objects

**TaskInput**: `prompt` (string), `metadata` (map of string to string; the customer puts what its success check needs here, such as `task_id`).

**ToolCall**: `id` (string, minted by the model provider), `name` (string), `arguments` (string, JSON text as the provider returned it).

**Message**: `role` (`MessageRole`), `content` (string or null), `tool_calls` (list of `ToolCall`, empty when none), `tool_call_id` (string or null; set on `tool` messages).

## Resources

### Project

`id`, `name`, `slack_webhook_set` (bool), `created_at`, `updated_at`.

| Operation | Path | Caller | Request | Response |
| --- | --- | --- | --- | --- |
| `getProjectSelf` | `GET /v1/projects.self` | P/K | none | `project` |
| `setProjectSlackWebhook` | `POST /v1/projects.setSlackWebhook` | P | `webhook_url` (string or null to clear) | `project` |

### ApiKey

`id`, `name`, `prefix` (first 12 characters, for display), `created_at`, `created_by_id`, `last_used_at` (or null), `revoked_at` (or null), `revoked_by_id` (or null).

| Operation | Path | Caller | Request | Response |
| --- | --- | --- | --- | --- |
| `createApiKey` | `POST /v1/api-keys.create` | P | `name` | `api_key`, `secret` (the full key, returned only here) |
| `listApiKeys` | `POST /v1/api-keys.list` | P | page | page of `ApiKey` |
| `revokeApiKey` | `POST /v1/api-keys.revoke` | P | `api_key_id` | `api_key` |

### Run

`id`, `agent_name`, `source` (`RunSource`), `parent_run_id` (or null; the run a replay came from), `replay_job_id` (or null), `replay_from_step` (or null), `task_input` (`TaskInput`), `status` (`RunStatus`), `step_count`, `final_output` (string or null), `latest_diagnosis_id` (or null), `created_by_id` (the API key), `started_at`, `finished_at` (or null).

| Operation | Path | Caller | Request | Response |
| --- | --- | --- | --- | --- |
| `startRun` | `POST /v1/runs.start` | K | `agent_name`, `task_input`, `replay_job_id` (or null) | `run` |
| `finishRun` | `POST /v1/runs.finish` | K | `run_id`, `status` (`RunOutcome`), `final_output` (or null) | `run` |
| `getRun` | `GET /v1/runs.get` | P/K | `run_id` | `run` |
| `listRuns` | `POST /v1/runs.list` | P | page, `statuses` (list or null), `sources` (list, default `["recorded"]`; null means every source), `agent_name` (or null) | page of `Run` |
| `countRuns` | `POST /v1/runs.count` | P | same filters as `listRuns` | `count` |

- `startRun` with a `replay_job_id` creates a `replay` run linked to the job's original run.
- `finishRun` on a `failed` recorded run triggers auto-diagnosis when the project has it on (always on during the hackathon).

### Step

`id`, `run_id`, `index` (1-based), `model` (string), `output` (`Message`, the assistant turn), `tool_results` (list of `Message` with role `tool`), `tokens_in`, `tokens_out`, `latency_ms`, `created_at`.

| Operation | Path | Caller | Request | Response |
| --- | --- | --- | --- | --- |
| `recordStep` | `POST /v1/steps.record` | K | `run_id`, `index`, `model`, `output`, `tool_results`, `messages` (the full message list after this step), `tokens_in`, `tokens_out`, `latency_ms` | `step` |
| `listSteps` | `POST /v1/steps.list` | P/K | page, `run_id` | page of `Step` |
| `getStepSnapshot` | `GET /v1/steps.getSnapshot` | P/K | `step_id` | `snapshot`: `{step_id, messages}` |

- `recordStep` is idempotent on (`run_id`, `index`): a repeat with the same index replaces nothing and returns the stored step.

### Diagnosis

`id`, `run_id`, `status` (`DiagnosisStatus`), `verdict_kind` (or null until done), `first_domino_step` (int or null), `search_low` and `search_high` (current bisect range, for the live view; null before the search starts), `verify_passes` and `verify_samples` (or null), `fixed_output` (`Message` or null; the rewritten step), `explanation` (`Explanation` or null), `cause_id` (or null), `check_count`, `replay_count`, `cost_usd`, `error_code` (or null), `created_by_id` (the person or API key; null for auto-diagnosis), `created_at`, `finished_at` (or null).

**Explanation**: `title`, `summary`, `suggested_fix`, `category` (`CauseCategory`).

| Operation | Path | Caller | Request | Response |
| --- | --- | --- | --- | --- |
| `createDiagnosis` | `POST /v1/diagnoses.create` | P/K | `run_id` | `diagnosis` |
| `getDiagnosis` | `GET /v1/diagnoses.get` | P/K | `diagnosis_id` | `diagnosis` |
| `listDiagnoses` | `POST /v1/diagnoses.list` | P | page, `run_ids`, `cause_ids`, `statuses`, `verdict_kinds` (each a list or null) | page of `Diagnosis` |
| `countDiagnoses` | `POST /v1/diagnoses.count` | P | same filters as `listDiagnoses` | `count` |

- Only failed recorded runs can be diagnosed. One diagnosis may run per run at a time (`409` otherwise).
- The web app polls `getDiagnosis` and `listChecks` every second while `status` is not `done` or `failed`.

### Check

`id`, `diagnosis_id`, `index` (order within the diagnosis), `phase` (`CheckPhase`), `save_point` (steps 1..`save_point` kept), `samples`, `passes`, `result` (`CheckResult`), `created_at`, `finished_at` (or null).

| Operation | Path | Caller | Request | Response |
| --- | --- | --- | --- | --- |
| `listChecks` | `POST /v1/checks.list` | P | page, `diagnosis_id` | page of `Check`, ordered by `index` |

### Cause

`id`, `title`, `category` (`CauseCategory`), `step_name` (string; the step's tool or role label), `summary`, `suggested_fix`, `run_count`, `verified_count`, `first_seen_at`, `last_seen_at`.

| Operation | Path | Caller | Request | Response |
| --- | --- | --- | --- | --- |
| `listCauses` | `POST /v1/causes.list` | P | page, `categories` (list or null) | page of `Cause`, most runs first |
| `getCause` | `GET /v1/causes.get` | P | `cause_id` | `cause` |
| `countCauses` | `POST /v1/causes.count` | P | same filters as `listCauses` | `count` |

The runs of a cause come from `listDiagnoses` with `cause_ids`.

### Benchmark

**BenchmarkScore**: `method` (`BenchmarkMethod`), `runs_scored`, `exact_accuracy`, `within_one_accuracy`, `verified_rate` (or null for methods without proof), `mean_cost_usd`, `mean_seconds`.

| Operation | Path | Caller | Request | Response |
| --- | --- | --- | --- | --- |
| `getLatestBenchmark` | `GET /v1/benchmarks.latest` | P | none | `benchmark`: `{id, created_at, scores: [BenchmarkScore]}` or null |

The benchmark is run by `fd-scripts`, which writes results to the database. There is no API to start one.

### Health

`GET /health` (operation `getHealth`, no auth, not under `/v1`) returns `{"ok": true}`.

## Worker protocol

The SDK worker runs on the customer side and only calls out.

| Operation | Path | Caller | Request | Response |
| --- | --- | --- | --- | --- |
| `leaseReplayJob` | `POST /v1/replay-jobs.lease` | K | `agent_names` (list), `wait_seconds` (0 to 20, default 10) | `replay_job` (`ReplayJob` or null when none arrived in time) |
| `submitReplayResult` | `POST /v1/replay-jobs.submit` | K | `replay_job_id`, `outcome` (`ReplayOutcome`), `replay_run_id` (or null), `error_code` (or null) | `replay_job` |

**ReplayJob**: `id`, `run_id` (the original run), `agent_name`, `task_input`, `from_step` (keep steps 1..`from_step`; 0 means start fresh), `messages` (the message list after `from_step`; the task's opening messages when 0), `replacement_output` (`Message` or null; when set, use it as the next step's model output instead of calling the model, then continue), `model_override` (string or null; when set, run the rest with this model), `status` (`ReplayJobStatus`), `lease_expires_at` (or null), `attempt`.

The worker loop:

1. `leaseReplayJob`. If null, lease again.
2. `startRun` with the job's `replay_job_id`, so the replay is recorded and visible.
3. Run the customer's agent from `messages`, honouring `replacement_output` and `model_override`, recording each step.
4. Run the customer's success check on the result. `finishRun`, then `submitReplayResult` with the outcome.
5. On a crash inside one job, `submitReplayResult` with `errored` and an `error_code`, then keep looping.

- A lease lasts `FD_API_LEASE_SECONDS` (default 120). A job whose lease ends goes back to `queued`; each lease raises `attempt`. A job whose lease ends after `FD_API_MAX_JOB_ATTEMPTS` (default 3) leases is `expired`.
- A submitted result ends the job: `succeeded` for a `passed` or `failed` outcome (the replay ran), `failed` for `errored`.
- `submitReplayResult` is idempotent by `replay_job_id`: the first result for a leased job counts, and any later one (a repeat, or a late result from an earlier lease) changes nothing.

## Engine ports

Defined in `fd_engine/ports.py` by the engine workstream (S1); implemented in `fd_api/adapters/` by S0. All methods are async.

| Port | Method | Meaning |
| --- | --- | --- |
| `RunReader` | `get_run(run_id) -> RunView` | The failed run, its task input and step count |
| `RunReader` | `get_steps(run_id) -> list[StepView]` | Its steps in order, with outputs, for explain and baseline |
| `ReplayRunner` | `replay(run_id, *, from_step, samples, model_override, replacement_output) -> list[ReplayOutcome]` | Enqueue `samples` replay jobs and wait for all outcomes (or a timeout, counted as `errored`) |
| `CheckSink` | `check_started(check) -> None`, `check_finished(check) -> None` | Persist each check so the web app can show it live |
| `CheckSink` | `progress(diagnosis_id, *, status, search_low, search_high) -> None` | Persist the live search range and status |

These are `fd-shared` models (`fd_shared.models`), frozen Pydantic models:

- **RunView**: `id`, `agent_name`, `task_input`, `status`, `step_count`, `final_output`.
- **StepView**: `index`, `model`, `output` (`Message`), `tool_results` (list of `Message`).
- **CheckView**: `diagnosis_id`, `index`, `phase`, `save_point`, `samples`, `passes`, `result`. A check is identified by (`diagnosis_id`, `index`); reporting the same pair again updates it.
- **DiagnosisResult**: `verdict_kind`, `first_domino_step`, `verify_passes`, `verify_samples`, `fixed_output`, `explanation` (`Explanation`), `check_count`, `replay_count`, `cost_usd`. The API stores it on the diagnosis.

Errors the engine raises derive from `fd_shared.errors` (`RetryableError` or `UnretryableError`); a diagnosis that stops on one stores its `code` in `error_code`.

## SDK public surface

What a customer writes. Exact signatures are settled by S2 inside these shapes.

```python
import first_domino as fd

# Recording: a no-op without FIRST_DOMINO_API_KEY, and never raises into the agent.
task = fd.TaskInput(prompt=..., metadata={"task_id": "t1"})
with fd.record(agent_name="call-assistant", task_input=task) as run:
    # Each chat completion through the wrapped client becomes a step (or call run.step).
    client = fd.wrap(OpenAI(), run)
    ...
    run.finish(status="failed", final_output=...)

# Replays, on the customer side.
worker = fd.Worker(agent_names=["call-assistant"])


# ctx carries messages, replacement_output, model_override and the replay run.
@worker.agent("call-assistant")
def replay(ctx: fd.ReplayContext) -> AgentResult: ...


@worker.success_check("call-assistant")
def check(task_input: fd.TaskInput, result: AgentResult) -> bool: ...


# Loops forever.
worker.run()

# Ask for a diagnosis from code.
fd.diagnose(run_id)
```

## Contract requests

Requests go in `docs/status/<stream>.md`, not here.
