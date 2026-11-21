# fd-database

Postgres tables and repositories for the control plane, on async SQLAlchemy 2. Tables are created at startup; there is no migration tool yet.

- **Layer:** Storage
- **May import:** `fd-shared`
- **Must never import:** `fd-engine`, `fd-api`
- **Rules:** [`.claude/rules/database.md`](../../.claude/rules/database.md)

## Modules

| Module | Job |
| --- | --- |
| `settings` | `DatabaseSettings`: connection URL and pool sizes. |
| `session` | Async engine, session factory and table creation at startup. |
| `pages` | Cursor keys for paged listings. |
| `tables/` | ORM tables: users, projects and API keys; runs and steps; replay jobs; diagnoses, checks and causes. |
| `repositories/` | One repository per aggregate, every method scoped by `project_id`: projects (and users), API keys, runs, steps, replay jobs, diagnoses (and checks), causes. |
| `testing` | A throwaway test database for the test suites. |
