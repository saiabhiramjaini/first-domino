# fd-shared

Typed domain models, enums, errors, the settings base class and logging, shared by every backend package.

- **Layer:** Shared
- **May import:** third-party libraries only
- **Must never import:** any `fd-*` package
- **Rules:** [`.claude/rules/shared.md`](../../.claude/rules/shared.md)

## Modules

| Module | Job |
| --- | --- |
| `enums` | Status, kind and category enums used across packages. |
| `errors` | `FirstDominoError`, `RetryableError` and `UnretryableError`, each with a stable code. |
| `settings` | The base class every package's settings class extends. |
| `logging` | Structured logging setup and `get_logger`. |
| `models/runs` | Task input and the run as the engine reads it. |
| `models/steps` | Messages and tool calls, in the OpenAI chat shape. |
| `models/diagnoses` | Checks, explanations and the engine's diagnosis result. |
