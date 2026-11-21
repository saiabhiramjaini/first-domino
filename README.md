# First Domino

Find the step where a failed AI agent run went wrong, and prove it.

First Domino records every run of your agent, live. When a run fails, it replays the run from its own save points, finds the first step after which the run always fails (the first domino), then rewrites that one step and replays again to prove the fix. Failures with the same first domino are grouped into root causes, which you can export as eval cases.

- Web app: https://first-domino.abhiramtech.in
- SDK: [`first-domino` on PyPI](https://pypi.org/project/first-domino/) (`pip install first-domino` or `uv add first-domino`)

## Use it

```python
import first_domino as fd

@fd.entrypoint("support-bot", check=lambda question, answer: "refund" in answer)
def answer(question: str) -> str:
    ...  # your agent, unchanged
```

```python
# worker.py, next to your agent: replays failed runs when First Domino asks
import first_domino as fd
import my_agent

fd.serve()
```

Set `FIRST_DOMINO_API_KEY` from the web app's Settings page. Every model call made through the OpenAI or Anthropic SDKs, or a framework built on them, is recorded. The SDK guide is [`server/packages/first-domino/README.md`](./server/packages/first-domino/README.md).

## How it works

1. **Record.** Each model call is a step, and every step is a save point.
2. **Search.** For a failed run, the engine asks whether the run can still pass when steps 1 to m are kept and the rest replayed. It binary-searches m for the first step after which no replay passes.
3. **Prove.** It rewrites that step and replays. If the run now passes, the step is proven to be the cause.
4. **Group.** It explains the failure and files it under a root cause with other runs that failed the same way.

Replays run in a worker on your side, so your code, tools and secrets never leave your machines. More in [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md).

## Repository

```
first-domino/
  server/              Python: API, engine, database and the SDK (uv workspace)
  client/              Next.js web app
  docs/                architecture, API contract, decisions, deploy and release guides
  .github/workflows/   server.yml, client.yml and sdk-release.yml
```

The server and the client are fully separate: each has its own tooling, dependencies, rules, environment file and CI. They meet only at the HTTP contract, `server/api/openapi.json`.

## Run it locally

Needs Python 3.12 with `uv`, Bun, Docker (running) and `jq`.

1. Copy `server/.env.example` to `server/.env` and fill in `OPENAI_API_KEY`, `FD_ENGINE_STRONG_MODEL` and `FD_API_WEB_JWT_SECRET`. Copy `client/.env.example` to `client/.env.local` and fill in the Google OAuth client, `AUTH_SECRET` and `API_JWT_SECRET` (the same value as `FD_API_WEB_JWT_SECRET`).
2. Install: `make install` in `server/`, `bun install` in `client/` (this also turns on the git hooks).
3. From `server/`: `make db-up`, then `make api` (port 8000; it creates the tables on start).
4. From `client/`: `bun run dev` (port 3000), and sign in with Google.
5. Follow the three steps on the Settings page to connect an agent. Point it at the local API with `FIRST_DOMINO_BASE_URL=http://localhost:8000`.

Checks: `make check` in `server/`, `bun run check` in `client/`.

## Docs

| File | What it covers |
| --- | --- |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | Components, data flow, the search and proof, the data model |
| [`docs/CONTRACT.md`](./docs/CONTRACT.md) | The HTTP API, the worker protocol, the engine ports and the SDK surface |
| [`docs/DECISIONS.md`](./docs/DECISIONS.md) | What is decided and why |
| [`docs/DEPLOY.md`](./docs/DEPLOY.md) | Production: Vercel, EC2, Neon and the CI/CD pipeline |
| [`docs/RELEASE.md`](./docs/RELEASE.md) | Publishing a new SDK version to PyPI |
| [`AGENTS.md`](./AGENTS.md) | Repo-wide rules for people and coding agents |
| [`server/README.md`](./server/README.md), [`client/AGENTS.md`](./client/AGENTS.md) | Working on each half |

## License

The SDK (`server/packages/first-domino`) is MIT licensed.
