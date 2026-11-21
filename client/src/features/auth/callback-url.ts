const DEFAULT_CALLBACK = "/runs";

export function safeCallbackUrl(value: string | string[] | undefined): string {
  if (typeof value !== "string") return DEFAULT_CALLBACK;
  // Browsers read a backslash as a slash, so "/\evil.com" would leave the site too.
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return DEFAULT_CALLBACK;
  }
  return value;
}
