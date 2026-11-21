import { z } from "zod";

import { zCauseCategory } from "@/api/generated/zod.gen";
import { CAUSE_CATEGORY } from "@/components/status/status-tones";
import type { Email } from "@/lib/email";

// The body fd-api posts when a diagnosis files a failure under a root cause seen for the
// first time.
export const NewCauseAlertSchema = z.object({
  to: z.email(),
  cause_id: z.uuid(),
  title: z.string().min(1).max(256),
  category: zCauseCategory,
  step_name: z.string().max(128),
  summary: z.string().max(4_000),
  suggested_fix: z.string().max(4_000),
  proven: z.boolean(),
});

export type NewCauseAlert = z.infer<typeof NewCauseAlertSchema>;

export function newCauseEmail(alert: NewCauseAlert, appUrl: string): Email {
  const link = new URL(`/causes/${alert.cause_id}`, appUrl).toString();
  const proof = alert.proven ? "Proven by replay" : "Not yet proven by replay";
  return {
    to: alert.to,
    subject: `New root cause: ${alert.title}`,
    text: [
      "First Domino found a new root cause in your agent's failed runs.",
      "",
      alert.title,
      `${CAUSE_CATEGORY[alert.category].label} · at ${alert.step_name} · ${proof}`,
      "",
      alert.summary,
      "",
      `Suggested fix: ${alert.suggested_fix}`,
      "",
      `Open it: ${link}`,
    ].join("\n"),
  };
}
