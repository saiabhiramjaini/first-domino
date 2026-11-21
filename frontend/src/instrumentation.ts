export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  const { attachProcessHandlers } = await import("./lib/process-handlers");
  attachProcessHandlers();
  const { log } = await import("./lib/log");
  for (const key of ["NEXT_PUBLIC_APP_URL", "NEXT_PUBLIC_API_URL"]) {
    if (!process.env[key]) log.warn({ key }, "instrumentation.missing_env");
  }
}

export async function onRequestError(
  err: unknown,
  request: { path: string; method: string; headers: { [key: string]: string | undefined } },
  context: {
    routerKind: "Pages Router" | "App Router";
    routePath: string;
    routeType: "render" | "route" | "action" | "middleware" | "proxy";
  }
): Promise<void> {
  const { log } = await import("./lib/log");
  const error = err instanceof Error ? err : new Error(String(err));
  const digest = "digest" in error && typeof error.digest === "string" ? error.digest : undefined;
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
