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
  }).catch(() => {
    // Reporting is best effort: the user already sees the error, and there is nowhere left to send this one.
  });
}
