# fd-database

Postgres tables and repositories for the control plane, on async SQLAlchemy 2. The schema is migrated with Alembic; the API upgrades the database at startup.

- **Layer:** Storage
- **May import:** `fd-shared`
- **Must never import:** `fd-engine`, `fd-api`
- **Rules:** [`.claude/rules/database.md`](../../.claude/rules/database.md)

## Modules

| Module | Job |
| --- | --- |
| `settings` | `DatabaseSettings`: connection URL and pool sizes. |
| `session` | Async engine, session factory and the schema migration at startup. |
| `schema` | Alembic upgrade under an advisory lock (stamping a pre-Alembic database at the baseline), revision writing, and the schema comparison. |
| `migrate` | `make migrate` and `make migration`. |
| `migrations/` | The Alembic environment and revisions. They ship in the wheel and are read through `importlib.resources`. |
| `pages` | Cursor keys for paged listings. |
| `tables/` | ORM tables: users, projects and API keys; runs and steps; replay jobs; diagnoses, checks and causes. |
| `repositories/` | One repository per aggregate, every method scoped by `project_id`: projects (and users), API keys, runs, steps, replay jobs, diagnoses (and checks), causes. |
| `testing` | A throwaway migrated test database for the test suites. |
