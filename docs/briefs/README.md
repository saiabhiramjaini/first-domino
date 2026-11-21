# Workstream briefs

Each file here is a complete starting prompt for one coding agent chat.

## How to start a workstream

1. Open the workstream's worktree (see `docs/PARALLEL_WORK.md`, "Git and merging").
2. Start a new Claude Code chat with that folder as the working directory.
3. Paste the whole brief as the first message.
4. The agent reads the files the brief lists, then starts with its first task.

| Brief | Start when |
| --- | --- |
| [`s0-platform-backend.md`](./s0-platform-backend.md) | Now. Everyone else depends on its first milestone |
| [`s1-engine.md`](./s1-engine.md) | Now |
| [`s2-customer-side.md`](./s2-customer-side.md) | Now (demo agent first; SDK after contract v1) |
| [`s3-web.md`](./s3-web.md) | Now (scaffold first; screens after contract v1) |
| [`s4-benchmark-deploy.md`](./s4-benchmark-deploy.md) | After milestone C3 (first end to end) |

## Talking between workstreams

Agents never edit each other's files. They write what they need in their own `docs/status/<id>.md`, and the user carries it across.
