import { formatSeconds } from "@/lib/format";

/** How long a run took, or has taken so far while it is still running. */
export function runDuration(startedAt: string, finishedAt: string | null, now: Date): string {
  const end = finishedAt ? new Date(finishedAt) : now;
  const seconds = Math.max(0, (end.getTime() - new Date(startedAt).getTime()) / 1000);
  return formatSeconds(seconds);
}
