import { isApiError } from "@/lib/api-error";

export type ErrorCopy = { title: string; description: string };

export function errorCopy(error: unknown, what: string): ErrorCopy {
  if (!isApiError(error)) {
    return { title: `Could not load ${what}`, description: "Try again in a moment." };
  }
  switch (error.code) {
    case "unauthenticated":
      return {
        title: "Your session has expired",
        description: "Sign in again to keep going.",
      };
    case "not_found":
      return {
        title: `No ${what} here`,
        description: "It may belong to another project or the link may be old.",
      };
    case "network_error":
      return {
        title: `Could not reach the API to load ${what}`,
        description: "Check your connection and that the API is running, then try again.",
      };
    case "unexpected_response":
      return {
        title: `Could not read ${what}`,
        description: "The web app and the API may be on different versions. Reload the page.",
      };
    default:
      return { title: `Could not load ${what}`, description: "Try again in a moment." };
  }
}
