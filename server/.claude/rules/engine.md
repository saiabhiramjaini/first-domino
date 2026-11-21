---
paths:
  - "packages/fd-engine/**"
---

# fd-engine rules

The engine is the core. It decides; it never does I/O of its own except model calls through `fd_engine.llm`.

- Depend only on `fd-shared` and the ports in `fd_engine.ports`. Never import `fd-database`, `fd-api`, `httpx` or a web framework.
- Ports are `typing.Protocol` classes: `ReplayRunner` (replay a run from a save point, k times), `RunReader` (load a run and its steps), `CheckSink` (record each check so the UI can show it). The API supplies the adapters.
- Every number in the bisect and verify rules is a field on `EngineSettings`: samples per check, verify threshold, fallback window, maximum checks, model ids, per-call timeouts.
- Bisect keeps the invariant "can succeed at `lo - 1`, doomed at `hi`". Write it as a docstring on the search function and test it.
- `can_succeed(0)` is false means a task or tool problem. Return that verdict kind; never blame step 1 for it.
- A verdict is "verified" only when the replay count that succeeded meets the threshold. Partial results are reported as such, never rounded up.
- The engine never decides success itself. Success comes from the customer's check, carried in each replay result.
- Explain and group are direct model calls with structured output. Each parse retries once, salvages, then degrades to an "unexplained" result.
- Keep each stage in its own module: `calibrate.py`, `bisect.py`, `verify.py`, `fallback.py`, `explain.py`, `group.py`, `baseline.py`.
- Test the search and verify logic with a fake `ReplayRunner` that returns scripted outcomes per save point. These tests need no network and no database.
