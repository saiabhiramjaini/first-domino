import type { Run } from "@/api/generated";
import { shortId } from "@/components/runs/short-id";
import { StatusBadge } from "@/components/status/status-badge";
import { RUN_SOURCE, RUN_STATUS } from "@/components/status/status-tones";
import { formatCount, formatDateTime } from "@/lib/format";
import { STEP_NOUN } from "@/lib/nouns";

type RunHeaderProps = { run: Run; actions: React.ReactNode };

export function RunHeader({ run, actions }: RunHeaderProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">{run.agent_name}</h1>
            <StatusBadge status={RUN_STATUS[run.status]} />
            <StatusBadge status={RUN_SOURCE[run.source]} />
          </div>
          <p className="text-sm text-muted-foreground">
            Run <span className="font-mono">{shortId(run.id)}</span> · started{" "}
            {formatDateTime(run.started_at)} · {formatCount(run.step_count, STEP_NOUN)}
          </p>
        </div>
        <div className="flex items-center gap-2">{actions}</div>
      </div>
      <blockquote className="rounded-xl border bg-card p-4 text-sm">
        <span className="mb-1 block text-xs font-medium text-muted-foreground">Task</span>
        <p className="whitespace-pre-wrap">{run.task_input.prompt}</p>
      </blockquote>
      {run.final_output && (
        <div className="rounded-xl border bg-card p-4 text-sm">
          <span className="mb-1 block text-xs font-medium text-muted-foreground">Final output</span>
          <p className="whitespace-pre-wrap">{run.final_output}</p>
        </div>
      )}
    </div>
  );
}
