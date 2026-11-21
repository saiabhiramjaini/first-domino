---
paths:
  - "packages/first-domino/**"
---

# first-domino SDK rules

This is the public package customers install from PyPI. Treat it as a published library: a change reaches customers only through a release (`docs/RELEASE.md`).

- Runtime dependencies are `httpx`, `pydantic` and `pydantic-settings` only. `openai` and `openai-agents` are optional extras for the lower-level adapters (`fd.wrap`, `first_domino.openai_agents`).
- Never import an `fd-*` package. Wire models live in `first_domino/_generated/`, generated from `api/openapi.json` by `make sdk-models`. Never edit generated files by hand.
- **Recording never breaks the customer's agent.** Every call to our API, and every step of HTTP capture, is wrapped so a failure is logged at debug level and swallowed. The agent must behave the same with or without First Domino.
- **Dark by default.** With no API key set, `@fd.entrypoint`, `record` and `wrap` record nothing.
- Capture reads model calls at the HTTP layer (`capture.py`) in the formats in `providers.py`. A new model API is a new provider there, not a framework adapter.
- The worker is the opposite: it owns its loop, so it may raise on bad configuration at start. Inside the loop, one failed job never stops the worker.
- Public API is what `first_domino/__init__.py` exports: `entrypoint`, `tool`, `set_outcome`, `serve`, `worker`, `init`, plus the lower-level `record`, `wrap`, `Worker` and `diagnose`. Everything else is private.
- Settings use the `FIRST_DOMINO_` prefix. `FIRST_DOMINO_BASE_URL` defaults to the hosted API.
- Every public function has a docstring with a short example, because it ends up in the README.
