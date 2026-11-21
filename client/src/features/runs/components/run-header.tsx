import { PageHeader } from "@/components/app-shell/page-header";
import { shortId } from "@/components/runs/short-id";
import { StatusBadge } from "@/components/status/status-badge";
import { RUN_STATUS } from "@/components/status/status-tones";
import type { Run } from "@/api/generated";
import { formatCount, formatDateTime } from "@/lib/format";
import { STEP_NOUN } from "@/lib/nouns";

type RunHeaderProps = { run: Run; title?: string; actions: React.ReactNode };

export function RunHeader({ run, title, actions }: RunHeaderProps) {
  return (
    <PageHeader
      eyebrow={
        <>
          <StatusBadge status={RUN_STATUS[run.status]} />
          <span className="font-mono">{run.agent_name}</span>
          {run.source === "replay" && <span>Replay</span>}
        </>
      }
      title={title ?? run.task_input.prompt}
      meta={
        <>
          <span className="font-mono">{shortId(run.id)}</span>
          <span>Started {formatDateTime(run.started_at)}</span>
          <span>{formatCount(run.step_count, STEP_NOUN)}</span>
        </>
      }
      actions={actions}
    />
  );
}
