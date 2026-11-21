---
name: code-design
description: >-
  Decides where new code or a new value belongs in the First Domino backend and keeps it
  simple, typed and single-purpose. Use for placement questions ("where should this live",
  "which package owns this"), structure questions ("split this", "is this modular",
  "extract this duplication"), and configuration questions ("add a setting", "constant or
  setting"). Do NOT use for pure bug fixes, one-line edits, formatting, dependency bumps, or
  as a routine check before every change; ruff and pyright cover the mechanical rules.
---

# Code design

Your job is the judgment the tooling cannot make: where a value goes, where code goes, and whether a new module earns its boundary. Ruff already enforces names, complexity, function length and commented-out code. Fix the design instead of silencing a rule.

## Where does a value go?

- **Tunable** (timeout, retry, sample count, threshold, limit, concurrency, model choice): a field on the owning package's `Settings` class.
- **Intrinsic** (header name, status code, regex, format string): a named module constant.
- **Domain object** (run, step, diagnosis, cause): a Pydantic model in `fd-shared` and a table in `fd-database`.

## Where does code go?

- **Respect the layers** in `AGENTS.md`. If the code needs an import a layer forbids, it is in the wrong package, or it needs a port in `fd_engine.ports`.
- **One function, one job.** Split parse, pure transform and persist. Keep the transform free of I/O so a unit test covers it.
- **A new concern gets a new module.** Do not grow an existing file into a second job. A new module must own a clear boundary, not collect leftovers.
- **Typed boundaries.** No mixed-value `dict` crosses a module boundary. Model it.
- **Reuse before you write.** Use the shared HTTP client, retry and model-output helpers. Extract a shared helper on the third copy, not the second.
- **Typed errors.** Raise a `RetryableError` or `UnretryableError` subclass with a stable code.

## Workflow

1. If the change is a bug fix, a one-liner, formatting or a dependency bump, stop. This skill does not apply.
2. Read the target module and one or two neighbours. Match their idiom.
3. Place the change with the checklists above.
4. If the change adds deterministic logic, add its unit test in the same change.
5. Run `make check`. If it fails, fix the cause; do not suppress.
6. If something does not fit the checklists, say so and ask instead of forcing it.

## Output

End with **Design notes**: two to four bullets on the boundary decision, any setting-or-constant placement, and the existing code you mirrored. No lecture, no restated lint rules, no full diff.

Illustrative:

> **Design notes**
> - Boundary: the replay outcome tally lives in `fd_engine/bisect.py` as a pure function, unit-tested with scripted outcomes.
> - Setting: samples per check became `EngineSettings.samples_per_check` (tunable).
