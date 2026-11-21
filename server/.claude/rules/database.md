---
paths:
  - "packages/fd-database/**"
---

# Working in `packages/fd-database/`

## Sessions and mappings

- SQLAlchemy 2.0 typed mappings (`Mapped[...]`, `mapped_column`) and `AsyncSession` only. Never call a synchronous session method.
- The session factory sets `expire_on_commit=False`, and no table declares a `relationship()`. Reading an attribute of a returned row therefore never does I/O. Adding a relationship is a decision: load it eagerly in every read.
- One module per table group under `fd_database/tables/`, one repository per aggregate under `fd_database/repositories/`.

## What a repository returns

**Return the row.** A repository hands back the ORM object, and the API's response model maps it once in a `from_row` classmethod. Do not copy a row into a dataclass or dict first; that adds a third shape that only repeats the second.

```python
# Bad: a record type that copies every column
async def get(self, *, project_id: UUID, run_id: UUID) -> RunRecord | None: ...


# Good: the row, mapped once at the contract edge
async def get(self, *, project_id: UUID, run_id: UUID) -> Run | None: ...
```

The one exception is a **computed row**: an aggregate (`group_by` with `func.count`, labelled expressions across a join) that no table represents. Give it a named Pydantic model. If a table row could have been returned instead, return the row.

## Plain queries, no authorization inside

- A repository answers facts. It never decides who may see a row. Keep the decision in the API, where the `403` or `404` is chosen.
- Prefer two plain reads over one clever query. A narrow fact question is fine: `is_owned_by(*, project_id, run_id) -> bool`.
- The exception is a filtered page, which cannot be filtered after the fact without breaking its paging. Name it for what it does (`list_failed`) so the filter is visible.

## Tenancy

- The project is the tenant. Every project-owned table has `project_id`, and every repository method takes `project_id` as a keyword argument and filters on it.
- Put the `project_id` predicate of a join in the `ON` clause. In `WHERE` it silently turns an outer join into an inner one.
- A child row reaches its project through a `NOT NULL` parent reference (a step through its run) only when that reference can never be null. Otherwise the child carries its own `project_id`.
- Pair a parent reference with the tenant where a row could name another project's parent: `FOREIGN KEY (project_id, run_id) REFERENCES runs (project_id, id)`.

## Columns

- Every table has `created_at` and `updated_at`.
- Every timestamp is `DateTime(timezone=True)`. Never a naive timestamp, and never patch a timezone onto a value at the API edge.
- Where a person or an API key causes an event, a `<verb>_at` column has a matching `<verb>_by_id`.
- Bound every text column: a name is 128 or 256, a slug 63.
- Statuses and kinds are Postgres enums built from the `StrEnum` in `fd-shared`, declared once and shared.
- Message snapshots and other large structured blobs are `JSONB`, validated through their `fd-shared` Pydantic model on write and read.
- A column default that repeats what every caller passes is noise. Leave it out.

## Constraints and indexes

- `project_id` leads every composite index and unique constraint, because every query carries it.
- A join table's primary key is its natural pair, not a surrogate id.
- Never put a unique constraint on a long string. Store a digest and make that unique (API keys store a SHA-256 hash).
- An index needs a query that uses it. Widen an existing index before adding a second.

## Writes

- Upserts use `insert(...).on_conflict_do_update(...).returning(...)`.
- Writes that must stay consistent run in one transaction.
- Retried writes are idempotent: a repeated replay result for the same job id changes nothing.
- Never build SQL by string concatenation.

## Schema changes

- Tables are created at startup by `create_all`. There is no migration tool yet; see `docs/DECISIONS.md`.
- A schema change therefore means dropping the local database. Say so in the change.

## Settings

- `DatabaseSettings` uses the `FD_DATABASE_` prefix. The URL is a `SecretStr`. Pool sizes and timeouts are fields, never inline numbers.
