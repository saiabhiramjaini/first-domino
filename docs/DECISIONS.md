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
| Auth | Clerk for people; hashed project API keys for the SDK | Sign-in in minutes; keys never stored in plain text |
| Models | Small OpenAI model for the demo agent; strongest available model for replays, fixes, explanations and the baseline judge. Ids only in settings | Realistic agent mistakes; fair replay checks |
| Contract | API owns it; SDK models generated from `api/openapi.json` | No hand-copied types |
| API style | Dot-action paths (`/runs.list`), verb-first operation ids, every listing a cursor page, errors with `code`, `title`, `detail` | One predictable shape for the SDK and the web client |
| Repositories | Return ORM rows; response models map them once; no authorization inside queries | Two shapes, not three; access decisions stay in the API |
| Tooling | ruff, pyright (standard), pytest with pytest-asyncio | Strict enough to keep quality, fast enough for one day |
| Hosting | One AWS EC2 instance with Docker Compose and Caddy | Same shape as local development |
| Demo domain | Doctor appointment booking for Indian clinics | Fits the Equal AI jury's own product; change only in the S2 brief |
| Projects | One project per person, created on first sign-in | No project screens needed for the demo |
| Live progress | The web app polls every second while a diagnosis runs | Simple and reliable behind a proxy |
| Parallel build | Five workstreams on their own branches and worktrees; contract first; API answers with example data until real handlers land | Agents can integrate from the first hour without waiting |
| Web stack | Next.js 16, Bun, shadcn/ui, React Query, react-hook-form with Zod, Pino, Clerk, client generated with `@hey-api/openapi-ts` | Owner's frontend scaffold plus the generated-client pattern |
| Repo layout | One repository with fully separate `backend/` (Python) and `frontend/` (Next.js); shared docs and `api/openapi.json` at the root | Each half has its own tooling, rules and CI; they meet only at the HTTP contract |
| Hooks | One root `pre-commit` config runs ruff in `backend/`, Prettier in `frontend/`, and the commit message check | Git hooks must live at the repository root; no Husky |
| Hosted runners | Not built. "What's next" slide: customer pushes a container we run in a sandbox | Too large for the hackathon |

## Open

| Question | Options | Default if nobody decides |
| --- | --- | --- |
| Publish the SDK to PyPI | Publish `0.1.0` on Sunday morning, or install from GitHub | Install from GitHub |
