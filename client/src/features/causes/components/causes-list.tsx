"use client";

import { TargetIcon } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/feedback/empty-state";
import { LoadMoreButton } from "@/components/feedback/load-more-button";
import { QueryError } from "@/components/feedback/query-error";
import { Panel } from "@/components/layout/panel";
import { StatusBadge } from "@/components/status/status-badge";
import { CAUSE_CATEGORY } from "@/components/status/status-tones";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useListCauses } from "@/hooks/api/use-list-causes";
import { formatCount, formatRelative } from "@/lib/format";
import { RUN_NOUN } from "@/lib/nouns";
import { pageItems } from "@/lib/paging";

const SKELETON_ROWS = ["a", "b", "c", "d"] as const;

export function CausesList() {
  const causes = useListCauses({});

  if (causes.isPending) {
    return (
      <Panel>
        <div className="flex flex-col gap-3 p-4" aria-busy="true">
          {SKELETON_ROWS.map((key) => (
            <Skeleton key={key} className="h-16 w-full" />
          ))}
        </div>
      </Panel>
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
      <Panel>
        <EmptyState
          icon={TargetIcon}
          title="No root causes yet"
          description="Each finished diagnosis groups its root cause here, so repeated failures show up as one cause with many runs."
          action={
            <Link href="/failures" className={buttonVariants({ variant: "outline" })}>
              See failed runs
            </Link>
          }
        />
      </Panel>
    );
  }

  const most = Math.max(...items.map((cause) => cause.run_count), 1);
  return (
    <Panel
      title={formatCount(items.length, { one: "cause", other: "causes" })}
      description="Most runs first. A cause is proven when a fix made its runs pass."
    >
      <ul className="flex flex-col divide-y">
        {items.map((cause) => (
          <li key={cause.id}>
            <Link
              href={`/causes/${cause.id}`}
              className="grid gap-3 px-4 py-4 outline-none hover:bg-muted/40 focus-visible:bg-muted/40 md:grid-cols-[minmax(0,1fr)_180px_120px] md:items-center md:gap-6"
            >
              <div className="flex min-w-0 flex-col gap-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={CAUSE_CATEGORY[cause.category]} dot={false} />
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {cause.step_name}
                  </span>
                </div>
                <span className="font-medium text-pretty">{cause.title}</span>
                <p className="line-clamp-1 text-sm text-muted-foreground">{cause.summary}</p>
              </div>
              <div className="flex flex-col gap-1.5">
                <div className="flex items-baseline justify-between gap-2 text-xs">
                  <span className="font-medium text-foreground">
                    {formatCount(cause.run_count, RUN_NOUN)}
                  </span>
                  <span className="font-mono text-verified">
                    {cause.verified_count}/{cause.run_count} proven
                  </span>
                </div>
                <span className="h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden="true">
                  <span
                    className="block h-full rounded-full bg-domino/70"
                    style={{ width: `${(cause.run_count / most) * 100}%` }}
                  />
                </span>
              </div>
              <span className="text-xs text-muted-foreground md:text-right">
                Last seen {formatRelative(cause.last_seen_at)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      {causes.hasNextPage && (
        <div className="border-t p-3">
          <LoadMoreButton
            hasNextPage={causes.hasNextPage}
            isFetchingNextPage={causes.isFetchingNextPage}
            onLoadMore={() => causes.fetchNextPage()}
          />
        </div>
      )}
    </Panel>
  );
}
