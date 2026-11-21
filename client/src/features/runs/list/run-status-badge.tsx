import type { RunStatus } from "@/api/generated";
import { StatusBadge } from "@/components/status/status-badge";
import { RUN_STATUS } from "@/components/status/status-tones";

// A run's status as a dot and a word; a running run's dot pulses.
export function RunStatusBadge({ status }: { status: RunStatus }) {
  return <StatusBadge status={RUN_STATUS[status]} />;
}
