import type { Diagnosis } from "@/api/generated";
import { isDiagnosisActive } from "@/hooks/api/diagnosis-activity";

// A replay is normally picked up within a second or two. Past this, say a worker is missing.
export const WORKER_WAIT_NOTICE_MS = 15_000;

type WaitInput = Pick<Diagnosis, "status" | "replays_waiting" | "waiting_since">;

/** How long replays have waited for a worker, in ms, or null when nothing is waiting. */
export function workerWaitMs(diagnosis: WaitInput, now: Date): number | null {
  if (!isDiagnosisActive(diagnosis.status)) return null;
  if (!diagnosis.replays_waiting || !diagnosis.waiting_since) return null;
  return Math.max(0, now.getTime() - new Date(diagnosis.waiting_since).getTime());
}

/** True when replays have waited long enough that no worker is probably running. */
export function isWaitingForWorker(diagnosis: WaitInput, now: Date): boolean {
  const waited = workerWaitMs(diagnosis, now);
  return waited !== null && waited >= WORKER_WAIT_NOTICE_MS;
}

/** "45 seconds", "3 minutes": how long, in words. */
export function waitedText(ms: number): string {
  const seconds = Math.round(ms / 1000);
  if (seconds < 90) return `${seconds} seconds`;
  return `${Math.round(seconds / 60)} minutes`;
}
