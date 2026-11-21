import type { Check } from "@/api/generated";

type DriftCheck = Pick<Check, "index" | "drifted" | "drift_tool_name">;

export type DriftSummary = { replays: number; toolName: string | null };

function byIndex<T extends Pick<Check, "index">>(checks: readonly T[]): T[] {
  return [...checks].sort((a, b) => a.index - b.index);
}

/** One check's drifted replays for the Checks table, or null when none drifted. */
export function driftText(check: Pick<Check, "drifted" | "drift_tool_name">): string | null {
  if (check.drifted === 0) return null;
  const count = `${check.drifted} drifted`;
  return check.drift_tool_name === null ? count : `${count} · ${check.drift_tool_name}`;
}

/** The tool named by the latest check that saw a drift: the one to mark with `@fd.tool`. */
export function latestDriftToolName(checks: readonly DriftCheck[]): string | null {
  return (
    byIndex(checks)
      .map((check) => check.drift_tool_name)
      .findLast((toolName) => toolName !== null) ?? null
  );
}

/** Every drifted replay of a diagnosis, or null when all of them matched the recording. */
export function driftSummary(checks: readonly DriftCheck[]): DriftSummary | null {
  const replays = checks.reduce((total, check) => total + check.drifted, 0);
  return replays === 0 ? null : { replays, toolName: latestDriftToolName(checks) };
}

/** Whether the search is still confirming that the success check fails the recorded run. */
export function isCalibrating(
  checks: readonly Pick<Check, "index" | "phase" | "result">[]
): boolean {
  const latest = byIndex(checks).at(-1);
  return latest?.phase === "calibrate" && latest.result === "pending";
}
