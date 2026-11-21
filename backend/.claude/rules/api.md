---
paths:
  - "packages/fd-api/**"
---

# Working in `packages/fd-api/`

The API is the control plane and owns the HTTP contract. `../api/openapi.json` is generated from it and checked in. The SDK models and, later, the web client are generated from that file, so the contract is the product: write it carefully.

## Routes

- One module and one router per resource under `fd_api/routers/`. Never add a resource's operations to another resource's module.
- Paths use dot actions under `/v1`: `/v1/<resource>.<action>`. Examples: `POST /v1/runs.list`, `GET /v1/runs.get`, `POST /v1/runs.start`, `POST /v1/diagnoses.create`, `POST /v1/replay-jobs.lease`. The full list is `docs/CONTRACT.md`.
- Use `.self` for the caller's own object without an id (`GET /v1/projects.self`). Use `.get` only when the request names an id.
- Every route sets `operation_id` in camelCase, verb first: `listRuns`, `getRun`, `createDiagnosis`, `leaseReplayJob`.
- Request and response models are named after the operation: `ListRunsRequest`, `ListRunsResponse`. A model for the object itself is named for the domain noun (`Run`, `Diagnosis`) with no `Response` suffix.
- Every operation that takes input has a request model. GET binds it from the query; writes and POST reads take a JSON body.
- A single object comes back in an envelope with one field named for it: `GetRunResponse(run=...)`.

## Listings

- Every listing is a page. The request extends `PageRequest` (`limit`, opaque `cursor`) and the response extends `PageResponse[T]` (`items`, `next_cursor`). A listing with no filters still declares an empty request subclass.
- Never expose an offset. Never add a total or per-status counts to a list response.
- A count is its own `<resource>.count` operation and a breakdown is `<resource>.group`, each taking the same filter model as `.list`.

## Errors

- Declare only the errors an operation can return.
- Every error body has `code`, `title` and `detail`. `code` is a stable snake_case value the SDK can branch on.
- Never echo submitted input or exception text in an error body.
- Inside a project an id is not a secret. A row the project has but the caller may not use answers `403`; a row the project does not have, including another project's, answers `404`.
- `.self` never declares `404`. A caller whose key or session is no longer valid gets `401`.

## Shape of a resource

- A stored column is a field. If the row stores it, the object reports it.
- Optional means the column is nullable today, not that it might be later.
- A closed set of values is a `StrEnum`, named for its domain (`RunStatus`, `DiagnosisStatus`, `CauseCategory`), never a bare noun such as `Status`.
- A field with only one possible value carries nothing. Leave it out until the second value exists.
- A request takes the fewest ids that find the resource. The project comes from the auth, never from the body.
- Never copy another resource's fields inline. Return its id, and let the caller get it.
- Fields that share a prefix are one object. Give it a named model and reuse it everywhere that group appears.
- Ids we mint are `UUID`. An id from an outside system is an opaque `str`, and its description names the system.
- An actor field ends in `_by_id`. A count ends in `_count`.
- Return nothing the caller already has, and no field nobody reads yet.

## Descriptions

- Write the field description when you write the field. A caller reads only the contract.
- A timestamp is described as `Time of <event>, in UTC RFC 3339 format.`
- An enum's meaning is described once, on the enum, not on every field that uses it.
- API text is US English. No em dashes, en dashes or the single-character ellipsis in published text; use commas, parentheses, periods and `...`.

## Auth

- People: verify the Clerk session token in a dependency in `fd_api/auth/users.py`. Read the project and membership from the database, never from token claims.
- SDK and worker: `Authorization: Bearer <api key>` in `fd_api/auth/api_keys.py`, checked by SHA-256 hash and `hmac.compare_digest`. Parse the scheme case-insensitively.
- Every handler receives `project_id` from the auth dependency and passes it to every repository call.

## Background work

- Diagnoses run as tracked background tasks in the `DiagnosisRunner` registry in `fd_api/services/`, never as a bare `create_task`.
- Adapters in `fd_api/adapters/` implement the engine ports over the repositories and the job queue.

## Worker protocol

- `leaseReplayJob` hands out at most one job, with a lease end time. `submitReplayResult` is idempotent by job id.
- An expired lease returns the job to `queued`. A late result for a job that was leased again is ignored.

## After a contract change

- Run `make openapi` and `make sdk-models`, and commit `../api/openapi.json` and the generated SDK models in the same change.
- A contract test in `packages/fd-api/tests/` compares the committed `../api/openapi.json` with the app's live schema and fails until they match.
