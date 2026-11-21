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
| `errors` | Error hierarchy: FirstDominoError, RetryableError, UnretryableError, each with a stable code. |
| `settings` | Settings base class that every package's settings class extends. |
| `logging` | Structured logging setup and get_logger. |
| `models/` | Domain models shared across packages. |
| `models/runs` | Run and run outcome models. |
| `models/steps` | Step, tool call, tool result and message snapshot models. |
| `models/replay_jobs` | Replay job and replay result models. |
| `models/diagnoses` | Diagnosis, check and verdict models. |
| `models/causes` | Root cause and cause group models. |

Status: layout only. Modules hold a docstring that states their job; no code yet.
