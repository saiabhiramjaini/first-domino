---
paths:
  - "packages/fd-shared/**"
---

# Working in `packages/fd-shared/`

## What belongs here

- What more than one package needs: domain models (`fd_shared.models`), enums, the error hierarchy, the settings base class, logging setup and small pure helpers.
- A helper moves here on its third use, not before.

## Import nothing internal

- This is the bottom layer. It imports third-party libraries only, never another `fd-*` package.
- No I/O, no network clients, no database code and no model calls. Importing this package must never do work.

## Models are plain data

- Pydantic v2 models, `frozen=True` unless they must change after creation.
- A field never holds a type from another package. Convert at the boundary that owns the other type.
- Fields that share a prefix are one named model.

## Enums

- Every status, kind and category is a `StrEnum`, named for its domain: `RunStatus`, `ReplayJobStatus`, `DiagnosisStatus`, `VerdictKind`, `CauseCategory`.
- A member is added here once and imported everywhere. The database and the API reuse the same enum.

## Settings base

- The base class reads `.env`, ignores unknown keys and is never instantiated at module scope.
- Each package subclasses it in its own `settings.py` with its own prefix.

## Errors

- `FirstDominoError` at the root, then `RetryableError` and `UnretryableError`.
- Each error class has a stable snake_case `code`. Callers branch on the class or the code, never on the message.
