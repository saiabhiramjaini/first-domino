# Web standards

The full rules for `client/`. Code templates for the scaffold live in [`docs/scaffold-reference.md`](./docs/scaffold-reference.md); where that file and this one differ, this file wins.

## Scaffold

Run once, from the repo root. `client/` already holds the rule files, so scaffold beside it and merge without overwriting them.

1. `bun create next-app frontend-tmp --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --no-git --use-bun --yes`, then `rsync -a --ignore-existing frontend-tmp/ client/ && rm -rf frontend-tmp`.
2. Runtime dependencies: `next@16`, `react@19`, `react-dom@19`, `zod@4`, `pino`, `clsx`, `tailwind-merge`, `react-hook-form`, `@hookform/resolvers`, `@tanstack/react-query`, `@tanstack/react-query-devtools`, `next-auth@beta` (Auth.js v5), `jose`. Add `zustand` only when the state rules below call for it.
3. Dev dependencies: `@hey-api/openapi-ts`, `vitest`, `@vitejs/plugin-react`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`, `pino-pretty`, `prettier`, `babel-plugin-react-compiler`.
4. shadcn, non-interactive: `bunx shadcn@latest init -d`, then `bunx shadcn@latest add button input label textarea dialog dropdown-menu badge sonner card separator skeleton tabs select checkbox switch tooltip popover sheet command avatar form table scroll-area`.
5. From the reference, every section it keeps (4, 6 to 9, 12, 13 to 17, 23 to 26): Prettier config, `src/lib/` files (`log.ts`, `app-environment.ts`, `get-ip.ts`, `process-handlers.ts`, `report-client-error.ts`, `utils.ts`), `/api/log/client-error`, `/api/health`, providers, Vitest, `.env.example`, `tsconfig` strict with `noUncheckedIndexedAccess`, `next.config.ts`, `instrumentation.ts`, and the error, not-found and loading pages. Replace `{{APP_NAME}}` with `first-domino-web`.
6. `next.config.ts` also sets `reactCompiler: true`.
7. `package.json` scripts: `dev`, `build`, `start`, `lint`, `format:check`, `typecheck` (`tsc --noEmit`), `test` (`vitest run`), `check` (lint, format check, typecheck, test in order), `generate:api`.
8. API client: `openapi-ts.config.ts` reads `../server/api/openapi.json` and writes `src/api/generated/` with the fetch client and the Zod plugin. Commit the generated output.
9. `Dockerfile` and `.dockerignore` from reference section 29. S4 deploys them.
10. `.github/workflows/client.yml` at the repo root: install, `bun run check`, `bun run build`, with `working-directory: client`. The backend has its own `server.yml`.

Husky lives here, in `client/.husky/` (`prepare`: `cd .. && husky client/.husky`), and its hooks cover both halves: ruff for staged backend files, Prettier for staged frontend files, and the `type: subject` commit message check. Not used from the reference: Vercel files and workflows (we deploy with Docker on EC2), `apiFetch` (replaced by the generated client), and its governance documents (replaced by this file, `AGENTS.md` and `REVIEW.md`).

## Structure

```
src/
  app/
    (marketing)/page.tsx        landing, public
    (auth)/sign-in/page.tsx       "Continue with Google"
    (app)/layout.tsx            signed-in shell
    (app)/failures/page.tsx
    (app)/runs/[runId]/page.tsx
    (app)/causes/page.tsx, causes/[causeId]/page.tsx
    (app)/benchmark/page.tsx
    (app)/settings/page.tsx
    api/auth/[...nextauth]/route.ts
    api/health/route.ts, api/log/client-error/route.ts
    error.tsx, global-error.tsx, not-found.tsx, loading.tsx, layout.tsx
  api/generated/                generated client and Zod schemas (never edit)
  hooks/api/                    one React Query hook per API operation
  features/<name>/              components/, schema.ts (form schemas), index.ts
  components/ui/                shadcn primitives
  components/<domain>/          shared pieces used by more than one feature
  lib/                          log, api client setup, errors, formatting, utils
  auth.ts                       NextAuth config: Google provider, JWT session, API token
  proxy.ts                      route protection for the signed-in routes
  instrumentation.ts
```

- A feature folder holds its screens and form schemas. Data hooks are shared and live in `src/hooks/api/`, because several features read the same operations.
- Import another feature only through its `index.ts`. A client component imports a feature sub-path, never its barrel, so server modules do not reach the browser bundle.
- A piece two features need goes to `src/components/<domain>/`, not into one feature. A missing primitive is added with `bunx shadcn@latest add`, never hand-written inline.

## Auth

- NextAuth (Auth.js v5) in `src/auth.ts` with the Google provider only and `session: { strategy: "jwt" }`. No database adapter.
- The `jwt` callback mints the **web session token** for the API with `jose`: HS256 signed with `API_JWT_SECRET`, claims `sub` (Google account id), `email`, `name`, `iss` `first-domino-web`, `aud` `first-domino-api`, 1 hour expiry. It re-mints when fewer than 5 minutes remain. The `session` callback exposes it as `session.apiToken`. The contract is `docs/CONTRACT.md`, "Auth".
- `src/proxy.ts` protects every route under `(app)`; signed-out visitors go to `/sign-in`. The landing page and `/api/health` stay public.
- The sign-in page has one button, "Continue with Google". `SessionProvider` wraps `Providers` in the root layout.
- Access is decided by the API. The browser only hides what the API would refuse anyway.
- Google OAuth redirect URI: `<NEXT_PUBLIC_APP_URL>/api/auth/callback/google`.

## Server and client components

- Components are server components by default. Add `"use client"` only for state, effects, handlers or browser APIs.
- `page.tsx` and `layout.tsx` stay server components. `params` and `searchParams` are Promises in Next 16; await them.
- Pass serializable props or `children` across the boundary, and only the fields the client uses. Never import a server component into a client file.
- Call `notFound()` when the record in the URL does not exist.

## Data

- The typed client comes from `src/api/generated/`. Configure its base URL from `NEXT_PUBLIC_API_URL` and attach the web session token in one place, `src/lib/api-client.ts` (from `auth()` on the server, `useSession()` in the browser).
- Client reads use a hook per operation in `src/hooks/api/`: `use-list-runs.ts`, `use-get-diagnosis.ts`. Writes use mutation hooks there: `use-create-diagnosis.ts`. A hook calls the generated function, checks the response with its generated Zod schema, and throws `ApiError` on failure.
- `ApiError` carries `status`, `code`, `title` and `detail` from the API's error body. Branch on `code`, never on text.
- Query keys are arrays that start with the resource: `["runs", "list", filters]`. Each hook exports its key so mutations can invalidate it.
- Fetch one record with its get operation. Never list and filter in the browser.
- Paging uses one shared helper over `next_cursor`. No hand-written paging loops in features.
- While a diagnosis is not `done` or `failed`, `useGetDiagnosis` and `useListChecks` refetch every second (`refetchInterval`), then stop.
- Never fetch with `useEffect` and `fetch`. React Query is the only client cache.
- Start independent reads together (`Promise.all` on the server, parallel hooks on the client).

## State

| The value is                                                    | Put it in                                               |
| --------------------------------------------------------------- | ------------------------------------------------------- |
| Used by one component                                           | `useState` there                                        |
| Used by a parent and a few children                             | State in the nearest common parent                      |
| Rarely changing, read across the tree (signed-in user, project) | A React context with a throwing `useX()` accessor       |
| Often changing and read across distant branches                 | One small Zustand store per concern in `src/lib/store/` |
| From the server                                                 | React Query through `src/hooks/api/`                    |
| A filter, tab or range a link should restore                    | URL search params, normalized on read                   |
| A form draft                                                    | `react-hook-form`                                       |

Debounce search input before it reaches a query key.

## Forms

- Every form uses `react-hook-form` with `zodResolver` and the shadcn `Form` components.
- The schema lives in the feature's `schema.ts`, at module scope. Every string field is trimmed, required where it must be, and capped, with user-facing messages ("Name is required").
- Default values cover every field. Nullable inputs use `value={field.value ?? ""}`.
- Submit through a mutation hook. Disable the button while pending and show a pending label.
- A server error goes to its field with `form.setError`, or to `"root"` when it has no field.

## Feedback and errors

- Every mutation ends in a toast: `toast.success` with what happened, or `toast.error` with how to fix it. Toasts come from shadcn `sonner`.
- Every caught client error is shown and reported: `reportClientError(error, "feature.action")` plus `toast.error`. Never an empty `catch`, never `alert()`.
- Render errors go to the nearest `error.tsx`, which shows a generic message and the digest. No stack or `err.message` reaches the page.
- Loading states use `loading.tsx` and `Skeleton` near the data, not a full-page spinner.

## Logging

- Server code logs with Pino from `@/lib/log`: `log.error({ runId, err }, "runs.load_failed")`. Context first, event name second, `feature.verb` in snake case.
- `console.*` is a lint error in app code.
- IP addresses appear only on `client.error_reported` and `request.error`.

## Styling and tokens

- Colors come from the shadcn tokens: `background`, `foreground`, `card`, `primary`, `secondary`, `muted`, `accent`, `destructive`, `border`, `input`, `ring`. Never `text-gray-500` or a hex value.
- No Tailwind arbitrary values. Use the scale; if nothing fits, an inline `style` prop, so every odd value stays visible.
- Status uses one tone map per domain key, in a `.ts` file, typed with `as const satisfies Record<RunStatus, Tone>`, rendered through a `Badge` variant. Never a ternary that picks a color class.
- The bisect colors carry meaning everywhere: search range, first domino, ruled out, verified. Define them once as tokens in `globals.css`.
- Header rows align with `items-center`. Layouts are mobile first and fluid (`w-full max-w-5xl`), never fixed pixel widths.

## Components

- Name a component for what it renders (`run-step-strip.tsx`), never `*-client.tsx`. Props are a named `type <Component>Props`.
- No boolean props that choose which subtree renders. Write explicit variants or separate components.
- A complex component is a set of small named exports around a context, not a namespace object.
- Extend shadcn primitives with `cva` variants. Never copy one to change it.
- Use `Link` for in-app navigation.

## React rules

- The React Compiler is on. Do not add `useMemo`, `useCallback` or `React.memo` for render speed.
- Derive values during render. An effect only syncs with something outside React, and cleans up what it starts.
- Key list rows on a stable id, never the index.

## Copy and formatting

- Sentence case everywhere. Buttons start with a verb ("Diagnose run", "Create API key").
- Address the reader as "you". Plain words.
- An error says what failed and how to fix it, next to what failed.
- An empty state says what will appear and how to get it ("No failed runs yet. Record a run with the SDK to see it here.").
- Dates and numbers use `Intl` through `@/lib/format`. No date libraries.

## Accessibility

- Semantic elements first. Every control is reachable by keyboard with a visible focus ring.
- An icon-only button has an `aria-label`.
- Hidden but mounted UI is `inert` and `aria-hidden`.

## Naming, imports and types

- Files are kebab-case; components are PascalCase; booleans start with `is`, `has` or `can`.
- Imports are grouped: external, then `@/`, then relative.
- No `any`. No `as` on input; parse it with Zod.
- Every `eslint-disable` has a reason on the same line.

## Environment

- `.env.example` lists every variable. `NEXT_PUBLIC_*` is public: it never holds a secret.
- Variables: `NEXT_PUBLIC_APP_URL`, `NEXT_PUBLIC_API_URL`, `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `AUTH_URL`, `API_JWT_SECRET` (same value as the backend's `FD_API_WEB_JWT_SECRET`), `APP_ENV` (build argument: `local`, `dev`, `prod`), `LOG_LEVEL`, `DD_SERVICE`.
- Read a server variable through a lazy getter. Never `throw` at module scope.

## Comments

- Default to no comment. When there is one, it explains a non-obvious technical reason and describes lasting behavior, never a plan, a ticket or debugging history.

## Tests

- Vitest. Test form schemas with direct `safeParse` cases, hooks with `renderHook` inside a `QueryClientProvider`, and components through `screen.getByRole`.
- Mock `fetch` at the edge, not the generated client.
- Do not chase coverage. Test what could silently break: schemas, the API error mapping, the status tone map, the bisect strip's state logic.
