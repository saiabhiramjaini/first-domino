"use client";

import { ArrowLeftIcon } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PageHeader } from "@/components/app-shell/page-header";
import { QueryError } from "@/components/feedback/query-error";
import { Panel } from "@/components/layout/panel";
import { MetricStrip } from "@/components/stats/metric-strip";
import { CAUSE_CATEGORY } from "@/components/status/status-tones";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useGetCause } from "@/hooks/api/use-get-cause";
import { isApiError } from "@/lib/api-error";
import { formatCount, formatDateTime, formatInteger, formatRelative } from "@/lib/format";
import { RUN_NOUN } from "@/lib/nouns";

import { CauseRunsTable } from "./cause-runs-table";
import { ExportTestsButton } from "./export-tests-button";

type CauseDetailProps = { causeId: string };

function BackToCauses() {
  return (
    <Link href="/causes" className={buttonVariants({ variant: "ghost", size: "sm" })}>
      <ArrowLeftIcon data-icon="inline-start" aria-hidden="true" />
      All root causes
    </Link>
  );
}

export function CauseDetail({ causeId }: CauseDetailProps) {
  const cause = useGetCause(causeId);

  if (isApiError(cause.error, "not_found")) notFound();

  if (cause.isPending) {
    return (
      <div className="flex flex-col gap-6" aria-busy="true">
        <BackToCauses />
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-24 w-full rounded-lg" />
        <Skeleton className="h-40 w-full rounded-lg" />
      </div>
    );
  }

  if (cause.isLoadingError) {
    return (
      <div className="flex flex-col gap-6">
        <BackToCauses />
        <QueryError
          error={cause.error}
          what="this root cause"
          source="causes.get"
          onRetry={() => cause.refetch()}
        />
      </div>
    );
  }

  const data = cause.data;
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow={
          <>
            <span className="font-mono">{data.step_name}</span>
            <span>{CAUSE_CATEGORY[data.category].label}</span>
          </>
        }
        title={data.title}
        description={data.summary}
        actions={<ExportTestsButton causeId={data.id} />}
      />

      <MetricStrip
        metrics={[
          { label: "Runs", value: formatInteger(data.run_count), hint: "Grouped under this cause" },
          {
            label: "Proven by a fix",
            value: formatInteger(data.verified_count),
            hint: `of ${formatCount(data.run_count, RUN_NOUN)}`,
          },
          {
            label: "First seen",
            value: formatRelative(data.first_seen_at),
            hint: formatDateTime(data.first_seen_at),
          },
          {
            label: "Last seen",
            value: formatRelative(data.last_seen_at),
            hint: formatDateTime(data.last_seen_at),
          },
        ]}
      />

      <Panel title="Suggested fix">
        <p className="p-4 text-sm text-pretty whitespace-pre-line">{data.suggested_fix}</p>
      </Panel>

      <Panel id="cause-runs" title="Runs with this cause">
        <CauseRunsTable causeId={causeId} />
      </Panel>
    </div>
  );
}
