# Backend rules

Rules for everything under `server/`: the API, the engine, the database, and the SDK. The repo-root `AGENTS.md` also applies (scope, parallel work, git). `CLAUDE.md` here only imports this file. Rules for one area live in `.claude/rules/<area>.md` and load when you touch the files they name.

Run every command in this file from `server/`.

## Coding principles

- One function, one job. Ruff caps complexity at 10 and length at 50 statements.
- A new concern goes in a new module. Never grow a file into a second job.
- Reuse the shared helper before writing a new one. Extract a shared helper on the third copy.
- Never edit `api/openapi.json` or `first_domino/_generated/` by hand. Change the API and regenerate.

## Package layers

The workspace is a `uv` monorepo under `packages/`. Imports flow one way only. "May import" is the full allow list; anything not in it is forbidden.

| Layer | Package | May import | Must never import |
| --- | --- | --- | --- |
| Shared | `fd-shared` | third-party only | any `fd-*` package |
| Storage | `fd-database` | `fd-shared` | `fd-engine`, `fd-api` |
| Logic | `fd-engine` | `fd-shared` | `fd-database`, `fd-api`, `first-domino` |
| Service | `fd-api` | `fd-shared`, `fd-database`, `fd-engine` | `first-domino` |
| Public SDK | `first-domino` | third-party only | any `fd-*` package |

- The engine never touches the database or HTTP. It depends on the `Protocol` ports in `fd_engine.ports`. The API provides the adapters.
- The SDK talks to the API only over HTTP. Customers use it from outside, so it gets no shortcut into the backend.
- The API owns the wire contract. `make openapi` writes `api/openapi.json`, and `make sdk-models` generates `first_domino/_generated/` from it. Never hand-copy a contract type.

## Typed boundaries

- Never pass a `dict` with mixed value types across a module boundary. Give it a name and a Pydantic model.
- A dict is fine when all keys share one type and all values share one type (`dict[str, int]`).
- Parse at the edge: request bodies, model output, environment and files become typed models immediately.
- Statuses, kinds and categories are `StrEnum` members, never bare strings.

## Configuration

Every value belongs in exactly one bucket.

- **Tunable** (timeouts, retries, sample counts, thresholds, limits, concurrency, model selection): a field on the package's `Settings` class in `settings.py`, built on `pydantic-settings`, loaded from the environment with the package prefix (`FD_ENGINE_`, `FD_API_`).
- **Domain object** (runs, steps, diagnoses, causes): a Pydantic model and a database table, not configuration.
- **Genuine constant** (header names, regexes, HTTP status codes, version pins): a named module-level constant.

Rules for settings:

- A class takes its settings by injection: `def __init__(self, settings: EngineSettings | None = None)`, then `self._settings = settings or EngineSettings()`.
- Never create a settings instance at module scope. Never read `os.environ` directly.
- Secrets are `SecretStr`. Model identifiers live only in settings, never in code.
- A provider key keeps its standard name. `OPENAI_API_KEY` is read into a `SecretStr` settings field through a validation alias and passed to the client explicitly.

## Locating files

- Never hardcode a repo-relative path at a call site, and never walk up from `Path(__file__)`.
- Data that ships inside a package is read with `importlib.resources.files("<package>")`.
- A path to a file read or written at run time (such as the OpenAPI export) is a settings field.

## Async

- Every I/O function is `async def`. Use one shared `httpx.AsyncClient` per process.
- Keep a strong reference to every background task. Start tasks in a `TaskGroup` or a registry that holds them until they finish.
- Never call `asyncio.run` inside a running event loop.

## Model calls

- All engine calls to OpenAI go through `fd_engine.llm`. No other module in `fd-shared`, `fd-database`, `fd-engine` or `fd-api` imports `openai`. The SDK's `wrap` and the demo agent are customer-side code and use it directly.
- Use structured output and parse it into a Pydantic model.
- Model output is untrusted. Every parse must **retry** once, **salvage** what is valid, and **degrade** to a safe default so one bad response never stops a diagnosis.
- Use a direct model call for judgment over data you already have (explain, group, judge). Only replays run the agent loop.
- Use plain code when a rule is enough. Success checks are code, not a model.
- Record tokens and cost for every call.

## Errors

- Errors derive from `fd_shared.errors.FirstDominoError` and their names end in `Error`.
- Split them into `RetryableError` and `UnretryableError`. Retry only the first kind.
- API error bodies have `code`, `title` and `detail`, where `code` is stable. Inside a project an id is not a secret: a row the caller cannot read answers `403`; a row the project does not have answers `404`.

## Security

- Every database query on a project-owned table filters by `project_id`.
- Store API keys as SHA-256 hashes and compare with `hmac.compare_digest`. Show the raw key once, at creation.
- Never log secrets, API keys, tokens or full `Authorization` headers.

## Logging

- Use `fd_shared.logging.get_logger`. Log structured fields with an event name: `log.info("diagnosis.started", run_id=run_id)`.
- Event names are `area.event` in snake case. Never build a message by string concatenation.
- Never use `print`. Log instead.

## Comments and docstrings

- Never restate in a comment what a type, ruff, a test or configuration already enforces.
- Public functions and classes get a short Google-style docstring. A docstring never promises behavior the code does not have.
- API-facing text (route summaries, field descriptions, error details) is US English with no em dashes. See `.claude/rules/api.md`.

## Testing

- Unit-test pure logic: bisect, verify decisions, output salvage, success checks. Use fakes for the ports, not mocks of every call.
- Do not test framework behavior or Python assignment.
- Keep one end-to-end test that runs ingest, diagnose, worker replay and verdict through the real API. Extend it rather than start a second one.
- A bug fix ships with a test that fails before the fix.
- When a shared helper replaces copies, at least one test runs the real helper, not a mock of it.
- Tests live in `packages/<package>/tests/`.

## Tooling gates

- `make check` runs ruff, pyright and pytest. Run it before you call a change done.
- Ruff runs on every edited Python file, and again over all packages when an agent stops, through the hooks in `.claude/settings.json`. They load when the agent chat is opened in `server/`.
- A `# noqa` or `# pyright: ignore` needs a reason on the same line. Do not add one to new code to hide a design problem.
- The `code-design` skill in `.claude/skills/` is for real placement questions, not a checkbox before every change.

## Where to read more

- `REVIEW.md` (in `server/`): the self-review checklist.
- `.claude/rules/`: the rules for each package. They carry decisions already made; read the one for the package you touch.
- `../docs/CONTRACT.md`, `../docs/ARCHITECTURE.md`, `../docs/DECISIONS.md`, `../docs/PARALLEL_WORK.md`.
