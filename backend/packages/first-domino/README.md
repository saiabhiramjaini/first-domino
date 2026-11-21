# first-domino

First Domino Python SDK: record agent runs and replay them on command with a self-hosted worker.

- **Layer:** Public SDK
- **May import:** third-party libraries only (`httpx`, `pydantic`, optional `openai`)
- **Must never import:** any `fd-*` package
- **Rules:** [`.claude/rules/sdk.md`](../../.claude/rules/sdk.md)

## Modules

| Module | Job |
| --- | --- |
| `settings` | SdkSettings: API key and base URL, read with the FIRST_DOMINO_ prefix. |
| `client` | Async HTTP client for the First Domino API. |
| `recorder` | record(): send each step of a run to First Domino without ever raising into the agent. |
| `wrap` | wrap(): record every call made through an OpenAI client. |
| `worker` | Worker: lease replay jobs, run the customer's agent and success check, submit results. |
| `diagnose` | diagnose(): ask First Domino to start a diagnosis of a run. |
| `errors` | SDK errors raised at worker start-up on bad configuration. |
| `cli` | Optional command line: login, worker and diagnose. |
| `_generated/` | Wire models generated from ../api/openapi.json by `make sdk-models`. Do not edit. |

Status: layout only. Modules hold a docstring that states their job; no code yet.
