# Scaffold reference

Code templates for setting up `frontend/`, taken from the project owner's frontend-only Next.js scaffold and trimmed to what First Domino uses. Section numbers match the original so [`../STANDARDS.md`](../STANDARDS.md) can point at them. **Where this file and `STANDARDS.md` differ, `STANDARDS.md` wins.**

Changes from the original:

- `{{APP_NAME}}` is `first-domino-web`.
- Removed: init and package lists (in `STANDARDS.md`), Husky, the `apiFetch` wrapper (replaced by the generated client), the feature folder and app structure sections (in `STANDARDS.md`), the governance document templates, the Vercel files and the CI template.
- `reportClientError` is always called with a `"feature.action"` string as its source.
- The toast component is shadcn `sonner`.
- `.env.example` adds the Clerk keys.

---

### 0. Exceptions, errors, logging, observability

Three layers. Do not mix them.

```
thrown Error in SSR / route     →   onRequestError + generic UI
API failure / Zod drift         →   user-safe toast + log.error
log.info / warn / error         →   stdout JSON. Operators only.
reportClientError(...)          →   POST /api/log/client-error → same Pino line
```

- Server components and the routes (`/api/health`, `/api/log/client-error`) never leak `err.message` or stacks to the browser.
- `error.tsx` shows a generic message and the `digest`. `reportClientError` sends the stack to the server log.
- Process: `uncaughtException` → `log.fatal` in Node-only `process-handlers.ts` (not inside `instrumentation.ts`). `unhandledRejection` → `log.error`.
- Forms: Zod via `zodResolver` plus `toast.error` or `form.setError`. Never a raw fetch error string.
- API responses are checked with their generated Zod schema. Drift becomes an `ApiError` and a toast, not a crash three components down.

| Level | When |
| --- | --- |
| `fatal` | The process is going down |
| `error` | SSR, route or API call failed; a client error was reported |
| `warn` | Recoverable |
| `info` | Rare in this app |
| `debug` | Off in production unless `LOG_LEVEL=debug` |

- Dual fields: `level` and GCP-style `severity`. `service` from `DD_SERVICE`.
- `APP_ENV=local|dev|prod` is a **build argument**. Browser source maps on local and dev, **off in prod**.
- `/api/health` returns `{ ok: true }`. Probe this, not `/`.

---

### 3. shadcn/ui rules

- Always install with `bunx shadcn@latest add <name>`. Never copy-paste a component by hand.
- Never duplicate a shadcn component. Extend it with `cva` variants.
- Compose complex UI from primitives. Do not rewrite them.

---

### 4. Prettier

`.prettierrc`:

```json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "plugins": []
}
```

`.prettierignore`:

```
node_modules/
.next/
out/
build/
dist/
*.lock
**/next-env.d.ts
**/*.tsbuildinfo
src/api/generated/
```

---

### 6. Core lib files

`src/lib/utils.ts` (shadcn installs it; verify):

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

`src/lib/log.ts` (server only):

```typescript
import pino, { type Logger, type LoggerOptions } from "pino";

const isProd = process.env.NODE_ENV === "production";
const isTest = process.env.NODE_ENV === "test";

const PINO_TO_SEVERITY: Record<string, string> = {
  trace: "DEBUG", debug: "DEBUG", info: "INFO",
  warn: "WARNING", error: "ERROR", fatal: "CRITICAL",
};

const baseOptions: LoggerOptions = {
  level: process.env.LOG_LEVEL ?? (isProd ? "info" : "debug"),
  serializers: { err: pino.stdSerializers.err, error: pino.stdSerializers.err },
  formatters: {
    level(label) {
      return { level: label, severity: PINO_TO_SEVERITY[label] ?? label.toUpperCase() };
    },
    bindings() {
      return { service: process.env.DD_SERVICE ?? "first-domino-web" };
    },
  },
  timestamp: pino.stdTimeFunctions.isoTime,
  redact: {
    paths: [
      "password", "*.password", "token", "*.token",
      "apiKey", "*.apiKey", "authorization", "*.authorization",
      "headers.authorization", "headers.cookie",
    ],
    censor: "[REDACTED]",
    remove: false,
  },
};

const devTransport: LoggerOptions["transport"] =
  !isProd && !isTest
    ? { target: "pino-pretty", options: { colorize: true, translateTime: "SYS:HH:MM:ss.l", ignore: "pid,hostname,service,severity" } }
    : undefined;

function buildDestination(): pino.DestinationStream | undefined {
  const appLogFile = process.env.APP_LOG_FILE;
  if (!appLogFile || devTransport) return undefined;
  try {
    const fileStream = pino.destination({ dest: appLogFile, mkdir: true, sync: false });
    fileStream.on("error", () => {});
    return pino.multistream([
      { stream: pino.destination({ dest: 1, sync: false }) },
      { stream: fileStream },
    ]);
  } catch (err) {
    process.stderr.write(
      `[log] APP_LOG_FILE unusable, stdout only: ${err instanceof Error ? err.message : String(err)}\n`
    );
    return undefined;
  }
}

const destination = buildDestination();

export const log: Logger = devTransport
  ? pino({ ...baseOptions, transport: devTransport })
  : destination
    ? pino(baseOptions, destination)
    : pino(baseOptions);
```

`src/lib/app-environment.ts`:

```typescript
export const APP_ENVIRONMENTS = ["local", "dev", "prod"] as const;
export type AppEnvironment = (typeof APP_ENVIRONMENTS)[number];
export type EnvironmentSettings = { enableBrowserSourceMaps: boolean };
export const ENVIRONMENT_SETTINGS: Record<AppEnvironment, EnvironmentSettings> = {
  local: { enableBrowserSourceMaps: true },
  dev: { enableBrowserSourceMaps: true },
  prod: { enableBrowserSourceMaps: false },
};
export function appEnvironment(value: string | undefined): AppEnvironment {
  return APP_ENVIRONMENTS.includes(value as AppEnvironment) ? (value as AppEnvironment) : "local";
}
```

`src/lib/get-ip.ts`:

```typescript
import type { NextRequest } from "next/server";
export function getIp(req: NextRequest): string {
  return (
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    req.headers.get("x-real-ip") ??
    "unknown"
  );
}
```

`src/lib/process-handlers.ts` (Node only, not in `instrumentation.ts`):

```typescript
import { log } from "./log";
export function attachProcessHandlers(): void {
  if ((globalThis as { __processHandlers?: boolean }).__processHandlers) return;
  (globalThis as { __processHandlers?: boolean }).__processHandlers = true;
  process.on("uncaughtException", (err) => {
    log.fatal({ err }, "process.uncaught_exception");
  });
  process.on("unhandledRejection", (reason) => {
    log.error(
      { err: reason instanceof Error ? reason : new Error(String(reason)) },
      "process.unhandled_rejection"
    );
  });
}
```

`src/lib/report-client-error.ts`:

```typescript
export function reportClientError(err: unknown, source: string): void {
  if (typeof window === "undefined") return;
  const message = err instanceof Error ? err.message : String(err);
  const stack = err instanceof Error ? err.stack : undefined;
  fetch("/api/log/client-error", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      message: message.slice(0, 2_000),
      stack: stack?.slice(0, 8_000),
      source: source.slice(0, 50),
      url: window.location.href.slice(0, 2_000),
    }),
    keepalive: true,
    credentials: "same-origin",
  }).catch(() => {});
}
```

`src/app/api/log/client-error/route.ts` (same origin, Zod, size cap, in-memory IP cap):

```typescript
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { log } from "@/lib/log";
import { getIp } from "@/lib/get-ip";

export const runtime = "nodejs";

const Schema = z.object({
  message: z.string().min(1).max(2_000),
  stack: z.string().max(8_000).optional(),
  source: z.string().min(1).max(50),
  url: z.string().max(2_000).optional(),
});

const buckets = new Map<string, { count: number; resetAt: number }>();
function allow(ip: string): boolean {
  const now = Date.now();
  const b = buckets.get(ip);
  if (!b || b.resetAt <= now) {
    buckets.set(ip, { count: 1, resetAt: now + 60_000 });
    return true;
  }
  if (b.count >= 10) return false;
  b.count += 1;
  return true;
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const origin = req.headers.get("origin");
  const app = process.env.NEXT_PUBLIC_APP_URL;
  if (origin && app && origin !== new URL(app).origin) {
    return new NextResponse(null, { status: 204 });
  }
  if (Number(req.headers.get("content-length") ?? 0) > 12_000) {
    return new NextResponse(null, { status: 413 });
  }
  const ip = getIp(req);
  if (!allow(ip)) return new NextResponse(null, { status: 429 });
  const parsed = Schema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return new NextResponse(null, { status: 400 });
  const err = new Error(parsed.data.message);
  if (parsed.data.stack) err.stack = parsed.data.stack;
  log.error({ err, source: parsed.data.source, client: { url: parsed.data.url, ip } }, "client.error_reported");
  return new NextResponse(null, { status: 204 });
}
```

---

### 7. Zod conventions

Zod is the only validation library. Use it at every boundary: form input, API responses, environment variables.

```typescript
const parsed = CreateApiKeySchema.safeParse(input);
if (!parsed.success) { /* handle */ }

const NameSchema = z
  .string({ message: "Name is required" })
  .trim()
  .min(1, { message: "Name is required" })
  .max(120, { message: "Name must be 120 characters or fewer" });

export const CreateApiKeySchema = z.object({ name: NameSchema });
export type CreateApiKeyInput = z.infer<typeof CreateApiKeySchema>;
```

- Messages are user-facing: "Name is required", not "name must be a string".
- `safeParse`, never `parse`, at a boundary.

| Boundary | Zod |
| --- | --- |
| Form input (`react-hook-form` + `zodResolver`) | Always |
| API response | Always (the generated schema) |
| Environment variable | At first use |
| Internal function calls | No, trust TypeScript |

---

### 8. Forms: react-hook-form + Zod

```tsx
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { CreateApiKeySchema, type CreateApiKeyInput } from "@/features/settings/schema";
import { useCreateApiKey } from "@/hooks/api/use-create-api-key";
import { reportClientError } from "@/lib/report-client-error";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";

export function CreateApiKeyForm() {
  const createApiKey = useCreateApiKey();
  const form = useForm<CreateApiKeyInput>({
    resolver: zodResolver(CreateApiKeySchema),
    defaultValues: { name: "" },
  });

  async function onSubmit(values: CreateApiKeyInput) {
    try {
      await createApiKey.mutateAsync(values);
      toast.success("API key created");
      form.reset();
    } catch (error) {
      reportClientError(error, "settings.create_api_key");
      form.setError("root", { message: "Could not create the key. Try again." });
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Key name</FormLabel>
              <FormControl><Input {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {form.formState.errors.root && (
          <p className="text-sm text-destructive">{form.formState.errors.root.message}</p>
        )}
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Creating..." : "Create API key"}
        </Button>
      </form>
    </Form>
  );
}
```

- One schema per form in the feature's `schema.ts`.
- Default values cover every field.
- A server error goes to `form.setError`. Field errors render through `<FormMessage />`.
- Disable submit while pending, with a pending label.
- Nullable inputs use `value={field.value ?? ""}`.

---

### 9. React Query provider

```tsx
// src/components/providers.tsx
"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 60 * 1000, refetchOnWindowFocus: false, retry: 1 },
        },
      })
  );

  return (
    <QueryClientProvider client={client}>
      {children}
      {process.env.NODE_ENV === "development" && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}
```

- One `QueryClient` per app, created with `useState` inside the provider.
- Query keys are arrays. A mutation's `onSuccess` invalidates the related queries.
- In the root layout, `ClerkProvider` wraps `Providers`.

---

### 12. Health route

```typescript
// src/app/api/health/route.ts
import { NextResponse } from "next/server";

export const runtime = "nodejs";

export function GET() {
  return NextResponse.json({ ok: true });
}
```

---

### 13. Vitest

`vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    env: {
      NEXT_PUBLIC_APP_URL: "https://app.test",
      NEXT_PUBLIC_API_URL: "https://api.test",
    },
  },
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
});
```

`src/test/setup.ts`:

```typescript
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
```

---

### 14. Environment variables

`.env.example`:

```bash
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
APP_ENV=local
LOG_LEVEL=debug
DD_SERVICE=first-domino-web
```

`.gitignore` adds `.env.local`, `.env.production`, `.env*.local`.

---

### 15. TypeScript

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "paths": { "@/*": ["./src/*"] }
  }
}
```

---

### 16. Styling

- File names are kebab-case; exported components are PascalCase.
- Semantic tokens only: `bg-background text-foreground border-border`, `text-muted-foreground`, `text-destructive`.
- Tailwind scale, not pixel values: `p-3.5 mt-8 w-80 text-sm`.
- Fluid widths: `w-full max-w-5xl`, `w-full md:w-1/2 lg:w-1/3`. Mobile first.
- `page.tsx` never has `"use client"`; push interactivity into a child client component.

---

### 17. Logger conventions

```typescript
log.info({ runId }, "runs.loaded");
log.error({ url, err }, "api.fetch_failed");
```

- Context object first, event name second, `feature.verb`.
- Client errors: `reportClientError(err, "runs.diagnose")` plus `toast.error`, never `console.error`.

---

### 23. `next.config.ts`

```typescript
import type { NextConfig } from "next";
import { ENVIRONMENT_SETTINGS, appEnvironment } from "./src/lib/app-environment";

const environment = ENVIRONMENT_SETTINGS[appEnvironment(process.env.APP_ENV)];

const nextConfig: NextConfig = {
  output: "standalone",
  reactCompiler: true,
  productionBrowserSourceMaps: environment.enableBrowserSourceMaps,
  serverExternalPackages: ["pino"],
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
```

---

### 24. `instrumentation.ts`

```typescript
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  const { attachProcessHandlers } = await import("./lib/process-handlers");
  attachProcessHandlers();
  const { log } = await import("./lib/log");
  if (!process.env.NEXT_PUBLIC_APP_URL) log.warn({ key: "NEXT_PUBLIC_APP_URL" }, "instrumentation.missing_env");
}

export async function onRequestError(
  err: unknown,
  request: { path: string; method: string; headers: { [key: string]: string | undefined } },
  context: {
    routerKind: "Pages Router" | "App Router";
    routePath: string;
    routeType: "render" | "route" | "action" | "middleware";
  }
): Promise<void> {
  const { log } = await import("./lib/log");
  const error = err instanceof Error ? err : new Error(String(err));
  const digest = (error as Error & { digest?: string }).digest;
  const xff = request.headers["x-forwarded-for"];
  const ip = xff?.split(",")[0]?.trim() ?? request.headers["x-real-ip"] ?? null;
  log.error(
    {
      err: error,
      digest,
      request: { path: request.path, method: request.method, ip },
      route: { kind: context.routerKind, path: context.routePath, type: context.routeType },
    },
    "request.error"
  );
}
```

---

### 25. Error, not-found and loading pages

`src/app/error.tsx`:

```tsx
"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { reportClientError } from "@/lib/report-client-error";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    reportClientError(error, "app.error_boundary");
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h2 className="text-lg font-semibold">Something went wrong</h2>
      {error.digest && <p className="text-sm text-muted-foreground">Reference: {error.digest}</p>}
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
```

`src/app/global-error.tsx`:

```tsx
"use client";

import { Button } from "@/components/ui/button";

export default function GlobalError({ reset }: { reset: () => void }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col items-center justify-center gap-4">
        <h2 className="text-lg font-semibold">Something went wrong</h2>
        <Button onClick={reset}>Try again</Button>
      </body>
    </html>
  );
}
```

`src/app/not-found.tsx`:

```tsx
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h2 className="text-lg font-semibold">Page not found</h2>
      <Button asChild variant="outline">
        <Link href="/">Go home</Link>
      </Button>
    </div>
  );
}
```

`src/app/loading.tsx`:

```tsx
export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
    </div>
  );
}
```

---

### 26. Metadata

Root layout metadata:

```tsx
import type { Metadata } from "next";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(APP_URL),
  title: { default: "First Domino", template: "%s | First Domino" },
  description: "Find the step where your AI agent's run started to fall. Proven, not guessed.",
  openGraph: {
    title: "First Domino",
    description: "Find the step where your AI agent's run started to fall. Proven, not guessed.",
    type: "website",
    url: APP_URL,
    siteName: "First Domino",
  },
  robots: { index: true, follow: true },
};
```

- `robots.ts` disallows `/api/` and the signed-in routes.
- `icon.png`, `apple-icon.png` and `opengraph-image.png` live in `src/app/`.
- Assets in `public/` use absolute paths, stay under 1 MB, and never hold secrets. Use `next/image` and `next/font`.

---

### 29. Dockerfile

```dockerfile
# syntax=docker/dockerfile:1.6

FROM oven/bun:1 AS deps
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

FROM oven/bun:1 AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG APP_ENV=dev
ARG NEXT_PUBLIC_APP_URL
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV APP_ENV=$APP_ENV
ENV NEXT_PUBLIC_APP_URL=${NEXT_PUBLIC_APP_URL}
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
ENV NEXT_TELEMETRY_DISABLED=1

RUN bun run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ARG APP_ENV=dev
ENV APP_ENV=$APP_ENV

RUN addgroup -S nodejs && adduser -S nextjs -G nodejs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

`.dockerignore`:

```
node_modules
.next
.git
.github
.vscode
.idea
.DS_Store
*.log
*.tsbuildinfo
.env
.env.local
.env*.local
coverage
**/dist
**/build
*.md
```
