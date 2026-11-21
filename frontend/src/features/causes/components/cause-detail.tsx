"use client";

import { ArrowLeftIcon } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PageHeader } from "@/components/app-shell/page-header";
import { QueryError } from "@/components/feedback/query-error";
import { StatCard } from "@/components/stats/stat-card";
import { StatusBadge } from "@/components/status/status-badge";
import { CAUSE_CATEGORY } from "@/components/status/status-tones";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useGetCause } from "@/hooks/api/use-get-cause";
import { isApiError } from "@/lib/api-error";
import { formatDateTime, formatInteger, formatRelative } from "@/lib/format";

import { CauseRunsTable } from "./cause-runs-table";

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
        <Skeleton className="h-24 w-full rounded-xl" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    );
  }

  if (cause.isError) {
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
      <div className="flex flex-col gap-3">
        <div>
          <BackToCauses />
        </div>
        <PageHeader title={data.title} description={`Step: ${data.step_name}`} />
        <div>
          <StatusBadge status={CAUSE_CATEGORY[data.category]} />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Runs" value={formatInteger(data.run_count)} />
        <StatCard
          label="Verified by replay"
          value={formatInteger(data.verified_count)}
          hint={`of ${formatInteger(data.run_count)} runs`}
        />
        <StatCard label="First seen" value={formatRelative(data.first_seen_at)} />
        <StatCard
          label="Last seen"
          value={formatRelative(data.last_seen_at)}
          hint={formatDateTime(data.last_seen_at)}
        />
      </div>

      <section className="flex flex-col gap-4 rounded-xl border bg-card p-5">
        <div className="flex flex-col gap-1.5">
          <h2 className="text-sm font-medium text-muted-foreground">What goes wrong</h2>
          <p className="text-sm">{data.summary}</p>
        </div>
        <div className="flex flex-col gap-1.5 rounded-lg border-l-4 border-verified bg-verified/10 p-4">
          <h2 className="text-sm font-medium">Suggested fix</h2>
          <p className="text-sm whitespace-pre-line">{data.suggested_fix}</p>
        </div>
      </section>

      <section className="flex flex-col gap-3" aria-labelledby="cause-runs-title">
        <h2 id="cause-runs-title" className="text-lg font-semibold">
          Runs with this cause
        </h2>
        <CauseRunsTable causeId={causeId} />
      </section>
    </div>
  );
}
