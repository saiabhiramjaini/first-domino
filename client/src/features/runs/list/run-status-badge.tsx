import type { RunStatus } from "@/api/generated";
import { StatusBadge } from "@/components/status/status-badge";
import { RUN_STATUS } from "@/components/status/status-tones";

// A run's status; a running run pulses so live work stands out in a list.
export function RunStatusBadge({ status }: { status: RunStatus }) {
  if (status !== "running") return <StatusBadge status={RUN_STATUS[status]} />;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-search-range/25 bg-search-range/10 px-1.5 py-0.5 text-xs font-medium text-search-range">
      <span className="relative flex size-1.5" aria-hidden="true">
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-current opacity-75 motion-reduce:animate-none" />
        <span className="relative inline-flex size-1.5 rounded-full bg-current" />
      </span>
      Running
    </span>
  );
}
