# fd-database

Postgres tables and repositories for the control plane, on async SQLAlchemy 2.

- **Layer:** Storage
- **May import:** `fd-shared`
- **Must never import:** `fd-engine`, `fd-api`
- **Rules:** [`.claude/rules/database.md`](../../.claude/rules/database.md)

## Modules

| Module | Job |
| --- | --- |
| `settings` | DatabaseSettings: connection URL and pool sizes. |
| `session` | Async engine, session factory and table creation at startup. |
| `tables/` | ORM table definitions. |
| `tables/base` | Declarative base and columns shared by every table. |
| `tables/projects` | Projects and API keys tables. |
| `tables/runs` | Runs and steps tables. |
| `tables/replay_jobs` | Replay jobs table. |
| `tables/diagnoses` | Diagnoses, checks and causes tables. |
| `repositories/` | Repositories: one per aggregate, every method scoped by project_id. |
| `repositories/projects` | Projects repository. |
| `repositories/api_keys` | API keys repository: create, look up by hash, revoke. |
| `repositories/runs` | Runs repository. |
| `repositories/steps` | Steps repository. |
| `repositories/replay_jobs` | Replay jobs repository: enqueue, lease, expire leases, record results. |
| `repositories/diagnoses` | Diagnoses and checks repository. |
| `repositories/causes` | Causes repository. |

Status: layout only. Modules hold a docstring that states their job; no code yet.
