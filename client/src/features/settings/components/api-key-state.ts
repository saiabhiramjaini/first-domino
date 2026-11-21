import type { ApiKey } from "@/api/generated";
import type { ToneLabel } from "@/components/status/tone";

type ApiKeyState = "active" | "revoked";

export const API_KEY_STATE = {
  active: { tone: "success", label: "Active" },
  revoked: { tone: "neutral", label: "Revoked" },
} as const satisfies Record<ApiKeyState, ToneLabel>;

export function apiKeyState(apiKey: Pick<ApiKey, "revoked_at">): ApiKeyState {
  return apiKey.revoked_at === null ? "active" : "revoked";
}
