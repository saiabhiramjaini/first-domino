import type { Instrumentation } from "next";

import { log } from "./lib/log";
import { attachProcessHandlers } from "./lib/process-handlers";

const REQUIRED_PUBLIC_ENV = ["NEXT_PUBLIC_APP_URL", "NEXT_PUBLIC_API_URL"] as const;

export function registerNode(): void {
  attachProcessHandlers();
  for (const key of REQUIRED_PUBLIC_ENV) {
    if (!process.env[key]) log.warn({ key }, "instrumentation.missing_env");
  }
}

type RequestErrorContext = {
  request: Parameters<Instrumentation.onRequestError>[1];
  route: Parameters<Instrumentation.onRequestError>[2];
};

function firstHeader(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export function logRequestError(err: unknown, { request, route }: RequestErrorContext): void {
  const error = err instanceof Error ? err : new Error(String(err));
  const digest = "digest" in error && typeof error.digest === "string" ? error.digest : undefined;
  const xff = firstHeader(request.headers["x-forwarded-for"]);
  const ip = xff?.split(",")[0]?.trim() ?? firstHeader(request.headers["x-real-ip"]) ?? null;
  log.error(
    {
      err: error,
      digest,
      request: { path: request.path, method: request.method, ip },
      route: { kind: route.routerKind, path: route.routePath, type: route.routeType },
    },
    "request.error"
  );
}
