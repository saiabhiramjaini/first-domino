const DEFAULT_CALLBACK = "/failures";

export function safeCallbackUrl(value: string | string[] | undefined): string {
  if (typeof value !== "string") return DEFAULT_CALLBACK;
  if (!value.startsWith("/") || value.startsWith("//")) return DEFAULT_CALLBACK;
  return value;
}
