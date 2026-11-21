"use client";

import { TargetIcon } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/feedback/empty-state";
import { QueryError } from "@/components/feedback/query-error";
import { StatusBadge } from "@/components/status/status-badge";
import { CAUSE_CATEGORY } from "@/components/status/status-tones";
import { Skeleton } from "@/components/ui/skeleton";
import { useListCauses } from "@/hooks/api/use-list-causes";
import { formatCount } from "@/lib/format";
import { RUN_NOUN } from "@/lib/nouns";
import { pageItems } from "@/lib/paging";

import { ALL_CAUSES, TOP_CAUSE_COUNT } from "../inbox-filters";

export function TopCauses() {
  const causes = useListCauses(ALL_CAUSES);
  if (causes.isError) {
    return (
      <div className="p-4">
        <QueryError
          error={causes.error}
          what="root causes"
          source="failures.load_causes"
          onRetry={causes.refetch}
        />
      </div>
    );
  }
  if (causes.isPending) {
    return (
      <div className="flex flex-col gap-3 p-4" aria-busy="true">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }
  const top = pageItems(causes.data).slice(0, TOP_CAUSE_COUNT);
  if (top.length === 0) {
    return (
      <EmptyState
        icon={TargetIcon}
        title="No root causes yet"
        description="Each finished diagnosis groups its cause here."
      />
    );
  }
  const most = Math.max(...top.map((cause) => cause.run_count), 1);
  return (
    <ol className="flex flex-col divide-y">
      {top.map((cause, index) => (
        <li key={cause.id}>
          <Link
            href={`/causes/${cause.id}`}
            className="flex gap-3 px-4 py-3 outline-none hover:bg-muted/40 focus-visible:bg-muted/40"
          >
            <span className="w-4 pt-0.5 font-mono text-xs text-muted-foreground tabular-nums">
              {index + 1}
            </span>
            <span className="flex min-w-0 flex-1 flex-col gap-2">
              <span className="line-clamp-2 text-sm font-medium">{cause.title}</span>
              <span className="flex items-center gap-2">
                <StatusBadge status={CAUSE_CATEGORY[cause.category]} dot={false} />
                <span className="text-xs text-muted-foreground">
                  {formatCount(cause.run_count, RUN_NOUN)}
                </span>
              </span>
              <span className="h-1 overflow-hidden rounded-full bg-muted" aria-hidden="true">
                <span
                  className="block h-full rounded-full bg-domino/70"
                  style={{ width: `${(cause.run_count / most) * 100}%` }}
                />
              </span>
            </span>
          </Link>
        </li>
      ))}
    </ol>
  );
}
