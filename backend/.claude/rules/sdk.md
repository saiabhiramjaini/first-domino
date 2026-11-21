---
paths:
  - "packages/first-domino/**"
---

# first-domino SDK rules

This is the public package customers install. Treat it as a published library.

- Runtime dependencies are `httpx`, `pydantic` and `pydantic-settings` only. `openai` is an optional extra used by `first_domino.wrap`.
- Never import an `fd-*` package. Wire models live in `first_domino/_generated/`, generated from `../api/openapi.json` by `make sdk-models`. Never edit generated files by hand.
- **Recording never breaks the customer's agent.** Every recorder and wrapper call to our API is wrapped so a failure is logged at debug level and swallowed. The customer's code path must behave the same with or without First Domino.
- **Dark by default.** With no API key set, `record` and `wrap` are no-ops.
- The worker is the opposite: it owns its loop, so it may raise on bad configuration at start. Inside the loop, one failed job never stops the worker.
- Public API is what `first_domino/__init__.py` exports: `record`, `wrap`, `Worker`, `diagnose`. Everything else is private (`_` prefix or not exported).
- Settings use the `FIRST_DOMINO_` prefix (`FIRST_DOMINO_API_KEY`, `FIRST_DOMINO_BASE_URL`).
- Every public function has a docstring with a short example, because it ends up in the README.
- The optional CLI (`first-domino login | worker | diagnose`) is a thin layer over the same public API.
