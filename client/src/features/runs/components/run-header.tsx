import { PageHeader } from "@/components/app-shell/page-header";
import { shortId } from "@/components/runs/short-id";
import { StatusBadge } from "@/components/status/status-badge";
import { RUN_SOURCE, RUN_STATUS } from "@/components/status/status-tones";
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
          <StatusBadge status={RUN_SOURCE[run.source]} dot={false} />
          <span className="font-mono">{run.agent_name}</span>
        </>
      }
      title={title ?? `${run.agent_name} run`}
      meta={
        <>
          <span>
            Run <span className="font-mono text-foreground/80">{shortId(run.id)}</span>
          </span>
          <span>Started {formatDateTime(run.started_at)}</span>
          <span>{formatCount(run.step_count, STEP_NOUN)}</span>
        </>
      }
      actions={actions}
    />
  );
}
