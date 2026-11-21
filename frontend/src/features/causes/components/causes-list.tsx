"use client";

import Link from "next/link";

import { EmptyState } from "@/components/feedback/empty-state";
import { LoadMoreButton } from "@/components/feedback/load-more-button";
import { QueryError } from "@/components/feedback/query-error";
import { StatusBadge } from "@/components/status/status-badge";
import { CAUSE_CATEGORY } from "@/components/status/status-tones";
import { Skeleton } from "@/components/ui/skeleton";
import { useListCauses } from "@/hooks/api/use-list-causes";
import { formatCount, formatRelative } from "@/lib/format";
import { RUN_NOUN } from "@/lib/nouns";
import { pageItems } from "@/lib/paging";

import { verifiedLabel } from "../cause-stats";

const SKELETON_ROWS = ["a", "b", "c"] as const;

export function CausesList() {
  const causes = useListCauses({});

  if (causes.isPending) {
    return (
      <div className="flex flex-col gap-3" aria-busy="true">
        {SKELETON_ROWS.map((key) => (
          <Skeleton key={key} className="h-28 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (causes.isError) {
    return (
      <QueryError
        error={causes.error}
        what="root causes"
        source="causes.list"
        onRetry={() => causes.refetch()}
      />
    );
  }

  const items = pageItems(causes.data);
  if (items.length === 0) {
    return (
      <EmptyState
        title="No root causes yet"
        description="Diagnose a failed run to group its cause here."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <ul className="flex flex-col gap-3">
        {items.map((cause) => (
          <li key={cause.id}>
            <Link
              href={`/causes/${cause.id}`}
              className="flex flex-col gap-3 rounded-xl border bg-card p-4 outline-none hover:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50 sm:flex-row sm:items-start sm:justify-between"
            >
              <div className="flex min-w-0 flex-col gap-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{cause.title}</span>
                  <StatusBadge status={CAUSE_CATEGORY[cause.category]} />
                </div>
                <span className="text-xs text-muted-foreground">Step: {cause.step_name}</span>
                <p className="line-clamp-2 text-sm text-muted-foreground">{cause.summary}</p>
              </div>
              <dl className="flex shrink-0 gap-4 text-sm sm:flex-col sm:items-end sm:gap-1">
                <div className="flex items-center gap-1">
                  <dt className="sr-only">Runs</dt>
                  <dd className="font-semibold tabular-nums">
                    {formatCount(cause.run_count, RUN_NOUN)}
                  </dd>
                </div>
                <div>
                  <dt className="sr-only">Verified</dt>
                  <dd className="text-verified">
                    {verifiedLabel(cause.verified_count, cause.run_count)}
                  </dd>
                </div>
                <div>
                  <dt className="sr-only">Last seen</dt>
                  <dd className="text-muted-foreground">
                    Last seen {formatRelative(cause.last_seen_at)}
                  </dd>
                </div>
              </dl>
            </Link>
          </li>
        ))}
      </ul>
      <LoadMoreButton
        hasNextPage={causes.hasNextPage}
        isFetchingNextPage={causes.isFetchingNextPage}
        onLoadMore={() => causes.fetchNextPage()}
      />
    </div>
  );
}
