# Web app rules

This is the First Domino web app: a frontend-only Next.js 16 app that talks to the First Domino API over HTTP. The repo-root `AGENTS.md` also applies (scope, no copied code, git). This file routes to the full rules.

| Before you...                           | Read                                                                                   |
| --------------------------------------- | -------------------------------------------------------------------------------------- |
| Set up the app for the first time       | [`STANDARDS.md`](./STANDARDS.md), "Scaffold"                                           |
| Build a screen, component, form or hook | [`STANDARDS.md`](./STANDARDS.md)                                                       |
| Review a change                         | [`REVIEW.md`](./REVIEW.md)                                                             |
| Need an API field or operation          | [`../docs/CONTRACT.md`](../docs/CONTRACT.md), then a request in `../docs/status/s3.md` |

## Non-negotiables

1. All data comes from the First Domino API through the generated client and a hook in `src/hooks/api/`. No first-party database, no server actions, no Redis. Sign-in is NextAuth with Google only, with JWT sessions and no database adapter.
2. API types, enums and status sets come from the generated client (`@/api/generated`). Never write a contract type or value list by hand.
3. Every API response is checked with its generated Zod schema. Every form uses `react-hook-form` with `zodResolver`.
4. `page.tsx` and `layout.tsx` are server components. Interactivity goes in child client components.
5. UI is built from the shadcn components in `src/components/ui/`. No raw `<button>`, `<input>`, `<select>` or `<textarea>` styled by hand.
6. Every color, size, radius and shadow is a token. No Tailwind arbitrary values (`[13px]`, `[#1a1a1a]`).
7. Server logs go through Pino (`@/lib/log`). Client errors go through `reportClientError` plus a toast. No `console.*`.
8. No secret in code and no secret behind `NEXT_PUBLIC_*` (`AUTH_SECRET`, `AUTH_GOOGLE_SECRET` and `API_JWT_SECRET` are server-only). No module-level `throw` on an env variable.
9. Never commit, push or open a pull request unless asked. Never pass `--no-verify`.

## Commands

Run from `client/`.

```bash
bun install
bun run dev            # http://localhost:3000
bun run generate:api   # regenerate the client from ../server/api/openapi.json
bun run check          # lint, format check, typecheck, tests
bun run build
```

`bun run check` passes before you call a change done.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
