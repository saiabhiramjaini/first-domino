# Web review checklist

Read [`AGENTS.md`](./AGENTS.md) and [`STANDARDS.md`](./STANDARDS.md) first. ESLint, Prettier and TypeScript already gate style and types; do not raise what they catch.

## 🔴 Must fix

- `"use client"` on a `page.tsx` or `layout.tsx`.
- An API response used without its generated Zod schema check.
- A contract type, enum or status list written by hand instead of imported from `@/api/generated`.
- Data fetched with `useEffect` and `fetch`, or an API call in a feature instead of a hook in `src/hooks/api/`.
- A secret in code or behind `NEXT_PUBLIC_*`, or a server-only module imported by a client component.
- A module-level `throw` on an environment variable.
- `err.message` or a stack shown on the page.
- A first-party database, server action, NextAuth or Redis added.
- `console.*` in app code, an empty `catch`, or `alert()`.

## 🟡 Should fix

- A mutation without a toast, without invalidating the related query, or without a pending state.
- A form without `react-hook-form` and `zodResolver`, or without complete default values.
- A raw form control or a hand-copied shadcn component.
- A Tailwind arbitrary value, a hardcoded color class, or a fixed pixel width.
- A ternary or second map that picks a status color instead of the one tone map.
- A boolean prop that chooses which subtree renders.
- A list filtered in the browser where a get operation exists, or a hand-written paging loop.
- `useMemo`, `useCallback` or `React.memo` added for render speed.
- An index used as a list key.
- An icon-only button without an `aria-label`.
- Title Case text, a button that does not start with a verb, or an error that does not say how to fix it.
- A file not in kebab-case, a `*-client.tsx` name, or inline props types.
- A comment that narrates the code or tells a debugging story.

## ⚪ Do not raise

- Formatting Prettier fixes.
- "Add Sentry, PostHog or Redis."
- Missing tests for trivial components.
- Theoretical races with no concrete path.

## Before you raise anything

- Read the whole file, not only the diff.
- Confirm a component, hook or token exists before you suggest it.
- If unsure, do not raise it unless it is 🔴 or 🟡 above.
