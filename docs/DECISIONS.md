# Decisions

Each entry states what was decided and why. Change an entry when a decision changes; do not keep history here.

## Decided

| Area | Decision | Why |
| --- | --- | --- |
| Category | SaaS for teams that run AI agents. Reference: LangSmith and Braintrust trace debugging, Sentry-style grouping | Plays to tracing, observability and eval experience |
| Product | First Domino: proven root causes for failed agent runs | Other tools guess the step; this one proves it by replay |
| Package names | SDK `first-domino` (import `first_domino`), published on PyPI under MIT; internal packages `fd-*` | One name everywhere; MIT so customers can use it freely |
| Core method | Bisect over save points, then verify by fixing one step and replaying | Cheap (about log2 of the step count in checks) and gives proof |
| Replays | Customer-side worker from the SDK polls jobs over HTTP | Customer code and secrets stay with the customer; no inbound endpoint |
| Success check | Customer-defined code, run by the worker | Plain code is free, fast and exact when the right answer is known |
| Backend | Python 3.12, FastAPI, async SQLAlchemy 2, Postgres, `uv` workspace | Async throughout; Postgres handles parallel replay writes |
| Schema changes | Alembic migrations inside `fd-database`, applied by the API at startup. A database created before Alembic is stamped at the baseline revision first | Contract 5 adds columns and an enum value to tables that already hold production data, which startup creation cannot do |
| Auth | People: Google sign-in through NextAuth (Auth.js v5, JWT sessions); the web server mints a short HS256 token for the API with a shared secret. SDK: hashed project API keys | No third-party auth service; the API stays stateless; keys never stored in plain text |
| Models | The agent's own model for search replays; the strongest available model for fixes and explanations. Ids only in settings | A stronger model in search replays recovers from mistakes the agent never would, so the search lands late |
| Contract | API owns it; SDK models generated from `server/api/openapi.json` | No hand-copied types |
| API style | Dot-action paths (`/runs.list`), verb-first operation ids, every listing a cursor page, errors with `code`, `title`, `detail` | One predictable shape for the SDK and the web client |
| Repositories | Return ORM rows; response models map them once; no authorization inside queries | Two shapes, not three; access decisions stay in the API |
| Tooling | ruff, pyright (standard), pytest with pytest-asyncio | Strict enough to keep quality, fast enough for one day |
| Hosting | Web on Vercel; API as one Docker container on EC2 behind nginx and certbot; Postgres on Neon; image on Docker Hub. CI/CD from GitHub Actions | Small, cheap, and every push to `main` ships |
| Example customers | Kept outside this repository and installing the SDK from PyPI like any customer: `call-assistant` (an AI call assistant with simulated callers, business rules plus an AI judge as its check, verifiers, evals and traffic) and `sdk-agents` (one refund agent built four ways: a plain OpenAI loop, LangChain, the OpenAI Agents SDK and the Anthropic SDK). Everyone in them is fictional | Real customer conditions, and proof the SDK works across frameworks |
| Projects | One project per person, created on first sign-in | No project screens needed for the demo |
| Live progress | The web app polls: runs every 2 seconds, a running diagnosis every second | Simple and reliable behind a proxy |
| Web stack | Next.js 16, Bun, shadcn/ui, React Query, react-hook-form with Zod, Pino, NextAuth with Google, client generated with `@hey-api/openapi-ts` | Owner's frontend scaffold plus the generated-client pattern |
| Repo layout | One repository with fully separate `server/` (Python) and `client/` (Next.js); shared docs at the root; the generated contract lives in `server/api/openapi.json` and is the only backend file the frontend reads | Each half has its own tooling, rules and CI; they meet only at the HTTP contract |
| Hooks | Husky, installed from `client/` (`prepare`: `cd .. && husky client/.husky`). `pre-commit` runs ruff on staged backend files and Prettier on staged frontend files, then re-stages them; `commit-msg` checks `type: subject` | Plain shell scripts the owner already uses; no Python `pre-commit` tool |
| SDK recording | Patch `send` on `httpx` and `httpx2` and read the model API's wire format (OpenAI Chat Completions, OpenAI Responses, Anthropic Messages), inside a run marked by `@fd.entrypoint` | Works with any framework built on those SDKs, with no adapter per framework |
| SDK replay | `fd.serve()` calls the customer's function again and answers model calls from the recording up to the save point; `@fd.tool` keeps side effects from repeating | Customers write no replay code |
| SDK release | A `sdk-v*` tag runs `sdk-release.yml`, which publishes with PyPI trusted publishing | No PyPI token stored anywhere |
| Check calibration | Before the search, replay keeping every step; the success check must fail it, or the diagnosis stops as `check_inconsistent` | The search assumes the run is doomed with all steps kept. A flaky check or a changed world would otherwise blame an innocent step. Kept steps are served from the recording, so it costs no model tokens |
| Replay drift | The SDK compares kept steps' tool results with the recording; a drifted replay stops early and is not evidence. All-drifted checks stop the diagnosis as `replay_not_faithful`, naming the tool | A replay whose kept steps differ from the recording tests a different run. Naming the tool turns a silent wrong verdict into a one-line fix (`@fd.tool`) |
| Search confidence | A save point with no passing replay gets a second round before it counts as doomed | One round of 3 wrongly blames a step 1 time in 8 when it passes half the time |
| Alerts | A new root cause emails the project owner. fd-api asks the web app (`/api/alerts/new-cause`), which sends with nodemailer through Gmail; Slack stays optional | One email per new problem, not per failed run, like a new issue in Sentry; the mail account lives with the web app |
| Restarts | Diagnoses hand themselves back on shutdown; recent ones restart from the beginning, older ones fail as interrupted | Deploys no longer lose diagnoses, and a crashing one cannot loop |
| UI | Almost monochrome: red only for a failed run, violet only for the first domino. Failures are a tab of the Runs list | Calm and easy to scan; color means something when it appears |
| Hosted runners | Not built. Later: the customer pushes a container we run in a sandbox | Too large for now |

## Open

| Question | Options | Default if nobody decides |
| --- | --- | --- |
| Hosted replays | Run customer containers in a sandbox, or keep the customer-side worker only | Customer-side worker only |
