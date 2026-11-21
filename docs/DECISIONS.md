# Decisions

Each entry states what was decided and why. Change an entry when a decision changes; do not keep history here.

## Decided

| Area | Decision | Why |
| --- | --- | --- |
| Track | Builders 2026, Track 3 (SaaS in a day). Reference: LangSmith and Braintrust trace debugging, Sentry-style grouping | Plays to tracing, observability and eval experience |
| Product | First Domino: proven root causes for failed agent runs | Other tools guess the step; this one proves it by replay |
| Package names | SDK `first-domino` (import `first_domino`); internal packages `fd-*` | `first-domino` was free on PyPI and npm when checked; not published yet |
| Core method | Bisect over save points, then verify by fixing one step and replaying | Cheap (about log2 of the step count in checks) and gives proof |
| Replays | Customer-side worker from the SDK polls jobs over HTTP | Customer code and secrets stay with the customer; no inbound endpoint |
| Success check | Customer-defined code, run by the worker | Plain code is free, fast and exact when the right answer is known |
| Backend | Python 3.12, FastAPI, async SQLAlchemy 2, Postgres, `uv` workspace | Async throughout; Postgres handles parallel replay writes |
| Schema changes | Tables created at startup; no migration tool | No deployed data to migrate during the hackathon |
| Auth | People: Google sign-in through NextAuth (Auth.js v5, JWT sessions); the web server mints a short HS256 token for the API with a shared secret. SDK: hashed project API keys | No third-party auth service; the API stays stateless; keys never stored in plain text |
| Models | Small OpenAI model for the demo agent; strongest available model for replays, fixes, explanations and the baseline judge. Ids only in settings | Realistic agent mistakes; fair replay checks |
| Contract | API owns it; SDK models generated from `api/openapi.json` | No hand-copied types |
| API style | Dot-action paths (`/runs.list`), verb-first operation ids, every listing a cursor page, errors with `code`, `title`, `detail` | One predictable shape for the SDK and the web client |
| Repositories | Return ORM rows; response models map them once; no authorization inside queries | Two shapes, not three; access decisions stay in the API |
| Tooling | ruff, pyright (standard), pytest with pytest-asyncio | Strict enough to keep quality, fast enough for one day |
| Hosting | One AWS EC2 instance with Docker Compose and Caddy | Same shape as local development |
| First customer | Equal AI. The demo shows First Domino diagnosing a replica of their call assistant, in a workspace named "Equal AI (demo)". Pitch it as "built for teams like Equal AI", never as an existing customer or partnership | The jury builds this exact kind of agent, so the value is obvious to them |
| Demo agent | Our replica of Equal AI's AI call assistant: answers calls for the user, talks to a scripted caller, then adds events, reminders and callbacks, blocks spam and sends a summary, using the user's personal context. No Equal AI logos, no real people; callers and businesses are fictional | It is the kind of agent the jury builds, so they recognise the failures at once; scripted callers keep replays deterministic |
| Projects | One project per person, created on first sign-in | No project screens needed for the demo |
| Live progress | The web app polls every second while a diagnosis runs | Simple and reliable behind a proxy |
| Parallel build | Five workstreams on their own branches and worktrees; contract first; API answers with example data until real handlers land | Agents can integrate from the first hour without waiting |
| Web stack | Next.js 16, Bun, shadcn/ui, React Query, react-hook-form with Zod, Pino, NextAuth with Google, client generated with `@hey-api/openapi-ts` | Owner's frontend scaffold plus the generated-client pattern |
| Repo layout | One repository with fully separate `backend/` (Python) and `frontend/` (Next.js); shared docs and `api/openapi.json` at the root | Each half has its own tooling, rules and CI; they meet only at the HTTP contract |
| Hooks | One root `pre-commit` config runs ruff in `backend/`, Prettier in `frontend/`, and the commit message check | Git hooks must live at the repository root; no Husky |
| Hosted runners | Not built. "What's next" slide: customer pushes a container we run in a sandbox | Too large for the hackathon |

## Open

| Question | Options | Default if nobody decides |
| --- | --- | --- |
| Publish the SDK to PyPI | Publish `0.1.0` on Sunday morning, or install from GitHub | Install from GitHub |
