# Parallel work plan

Several coding agents build First Domino at the same time, each in its own chat. This file says who owns what, what each needs from the others, and when the pieces meet. Every agent reads it before starting.

## Workstreams

| Id | Workstream | Owns (may edit) | Brief |
| --- | --- | --- | --- |
| S0 | Platform backend: contract, database, API | `server/packages/fd-shared/`, `server/packages/fd-database/`, `server/packages/fd-api/`, `api/`, `docs/CONTRACT.md`, `server/pyproject.toml`, `server/uv.lock`, `server/Makefile`, `server/compose.yaml`, `server/.env.example`, `.github/workflows/server.yml` | [`briefs/s0-platform-backend.md`](./briefs/s0-platform-backend.md) |
| S1 | Engine: bisect, verify, explain, group, baseline | `server/packages/fd-engine/` | [`briefs/s1-engine.md`](./briefs/s1-engine.md) |
| S2 | Customer side: demo agent and SDK | `server/packages/fd-demo-agent/`, `server/packages/first-domino/` | [`briefs/s2-customer-side.md`](./briefs/s2-customer-side.md) |
| S3 | Web app | `client/`, `.github/workflows/client.yml` | [`briefs/s3-web.md`](./briefs/s3-web.md) |
| S4 | Benchmark, deploy, demo assets (starts Saturday night) | `server/packages/fd-scripts/` (taken over by S1; no deployment for now) | [`briefs/s4-benchmark-deploy.md`](./briefs/s4-benchmark-deploy.md) |

Everyone may edit their own `docs/status/<id>.md`. Nobody edits another workstream's files. Rule files (`AGENTS.md`, `server/AGENTS.md`, `server/REVIEW.md`, `server/.claude/`, `client/AGENTS.md`, `client/STANDARDS.md`, `client/REVIEW.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, this file) change only when the user asks.

Paths in this file and in the briefs are from the repo root. Backend agents open their chat in `server/`, the frontend agent in `client/`.

## What each workstream needs from the others

```
            docs/CONTRACT.md (S0)
       ┌──────────┼──────────────┬───────────────┐
       ▼          ▼              ▼               ▼
  fd-api (S0)  fd-engine (S1)  SDK + demo (S2)   web (S3)
       ▲          │ ports.py
       └──────────┘ S0 writes adapters for S1's ports
```

| Needs | From | Unblocked by |
| --- | --- | --- |
| S1 engine | nothing to start; S0's adapters to run for real | Engine runs on fakes until the API adapters land |
| S2 demo agent | nothing to start | Mock world, agent loop and success check need no backend |
| S2 SDK | contract v1 and the generated SDK models | S0 milestone C1 |
| S3 web | contract v1 and `server/api/openapi.json` | S0 milestone C1; S3 scaffolds the app before that |
| S0 adapters | S1's `fd_engine/ports.py` | S1 commits the ports first |
| S4 | everything | C3 |

## Contract first, stubs that answer

S0's first job is **contract v1**: the `fd-shared` models and enums, every route in `docs/CONTRACT.md` with its request and response models, and `server/api/openapi.json`. Every route answers with **fixed example data** (from `fd_api/examples.py`) until the real handler lands, so S2 and S3 can integrate against a running API from the first hour. Replacing examples with real handlers does not change the contract.

## Milestones

Times assume work starts Saturday afternoon. If you start later, keep the order and shrink the gaps, not the buffer.

| Id | When | Done means |
| --- | --- | --- |
| C1 | Sat, start + 1.5 h | Contract v1 merged: `server/api/openapi.json`, SDK models generated, API runs with example data. S1 has committed `ports.py` |
| C2 | Sat, start + 4.5 h | S1: bisect and verify pass unit tests on fakes. S2: demo agent completes and fails tasks locally with save points. S0: runs and steps stored for real. S3: shell, sign-in and inbox render example data |
| C3 | Sat night | First end to end: demo agent records a failed run, auto-diagnosis runs, the worker replays, the verdict is stored and shows in the web app |
| C4 | Sun 6:30 AM | Labelled dataset and first benchmark numbers. Web shows live bisect and verdict |
| C5 | Sun 9:30 AM | Deployed on AWS with a public HTTPS link |
| C6 | Sun 11:00 AM | Feature freeze. Only fixes, the demo video, slides and README after this |
| C7 | Sun 1:30 PM | Submitted. Code freeze is 2:00 PM |

## Git and merging

- One repository. `main` is always runnable.
- Each workstream works on its own branch in its own worktree: `stream/s0-platform`, `stream/s1-engine`, `stream/s2-customer`, `stream/s3-web`, `stream/s4-ops`.
- The user merges into `main` at each milestone, S0 first. After a merge, every workstream rebases or merges `main` into its branch.
- `server/uv.lock` conflicts are resolved by taking either side and running `uv lock` in `server/`. Never hand-edit it.
- Commits follow `AGENTS.md`: one line, `type: subject`. Agents commit on their own branch only when the user has said they may.

## Status files

Each workstream keeps `docs/status/<id>.md` current, in this shape:

```
# S1 status
Updated: <time>
Milestone: C2 (on track | at risk | blocked)
Done: short bullets
Doing: one line
Blocked by: nothing | what, and from whom
Contract requests: none | the change and why
```

Update it at the end of every work block and before the user merges. It is the only way workstreams talk to each other, apart from the user.

## Definition of done for any task

- Backend: `make check` passes in `server/`. Frontend: `bun run check` passes in `client/`.
- The change follows `AGENTS.md`, its half's `AGENTS.md`, the rule file for its area, and its half's `REVIEW.md`.
- New pure logic has a unit test.
- The status file says what changed.
