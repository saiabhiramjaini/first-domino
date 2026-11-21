# Review checklist

Use this before you call a change done, and when you ask a coding agent to review a diff. It decides what is worth raising. Ruff, pyright and pytest already gate style and types, so do not raise what they catch.

## 🔴 Must fix

- **Cross-project leak.** A query on a project-owned table with no `project_id` filter.
- **Layer break.** An import that `AGENTS.md` forbids, such as `fd-engine` importing `fd-database`, or the SDK importing an `fd-*` package.
- **Hand-copied contract.** An SDK or demo-agent type written by hand instead of generated from `../api/openapi.json`.
- **Plain secret.** An API key stored or compared in plain text, a secret in a log line, or a secret value committed anywhere.
- **Unguarded model output.** `json.loads` or a parse of model output whose failure can stop a diagnosis.
- **Lost background task.** `asyncio.create_task` with no strong reference held until the task ends.
- **Recorder breaks the customer.** An SDK recording or worker failure that raises into the customer's agent code.
- **Wrong verdict.** A change to bisect or verify that can mark a step as verified when fewer than the configured number of replays succeeded.
- **Join without the tenant.** A join onto a project-owned table with no `project_id` predicate in its `ON` clause.
- **Repository decides access.** A repository read that returns the verdict, or returns `None` for both "missing" and "not yours", so the API cannot tell `404` from `403`.
- **Non-idempotent retry path.** A replay result or worker callback that double-counts when delivered twice.
- **Stale contract.** A route or model change without the regenerated `../api/openapi.json` and SDK models.

## 🟡 Should fix

- A tunable written inline instead of a settings field. A model id anywhere outside settings.
- A settings instance created at module scope, or `os.environ` read directly.
- A `dict` with mixed value types crossing a module boundary.
- A status or kind typed as `str` instead of a `StrEnum`.
- A model call where a plain rule is enough, or an agent loop where one direct model call is enough.
- An error matched by its message text.
- A listing that is not a page (`PageRequest` and `PageResponse[T]`), or a list response that carries a total.
- A path that is not `/<resource>.<action>`, an `operation_id` that is not verb first, or a request or response model not named after its operation.
- An error body without `code`, `title` and `detail`, or one that echoes input.
- A naive timestamp column, or a timezone patched on at the API edge.
- A repository that copies a row into a second record type instead of returning the row.
- A resource field that copies another resource's data, repeats a field, or has one possible value.
- An enum named for a bare noun (`Status`) instead of its domain (`RunStatus`).
- Em dashes or British spelling in API-facing text.
- A hardcoded repo path or a `Path(__file__)` walk.
- New pure logic in the engine with no unit test.
- A comment that narrates the code or tells the debugging story.

## ⚪ Do not raise

- Style that ruff fixes on its own.
- Theoretical races with no concrete path.
- Missing tests for trivial helpers.
- Rate limits and load concerns below a concrete number.
- Renames or refactors that do not change behavior.

## Before you raise anything

- Read the whole file, not only the diff.
- Confirm a helper, setting or symbol exists before you suggest it.
- Match the pattern the code already uses.
- If unsure, do not raise it unless it is 🔴 or 🟡 above.
