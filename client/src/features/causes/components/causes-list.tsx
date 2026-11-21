"use client";

import { TargetIcon } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/feedback/empty-state";
import { LoadMoreButton } from "@/components/feedback/load-more-button";
import { QueryError } from "@/components/feedback/query-error";
import { Panel } from "@/components/layout/panel";
import { CAUSE_CATEGORY } from "@/components/status/status-tones";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useListCauses } from "@/hooks/api/use-list-causes";
import { formatInteger, formatRelative } from "@/lib/format";
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

  if (causes.isLoadingError) {
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
            <Link href="/runs?status=failed" className={buttonVariants({ variant: "outline" })}>
              See failed runs
            </Link>
          }
        />
      </Panel>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Cause</TableHead>
            <TableHead className="text-right">Runs</TableHead>
            <TableHead className="text-right">Proven</TableHead>
            <TableHead className="text-right">Last seen</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((cause) => (
            <TableRow key={cause.id}>
              <TableCell className="max-w-[36rem] whitespace-normal">
                <Link
                  href={`/causes/${cause.id}`}
                  className="flex min-w-0 flex-col gap-0.5 rounded-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  <span className="font-medium text-pretty">{cause.title}</span>
                  <span className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
                    <span className="font-mono">{cause.step_name}</span>
                    <span aria-hidden="true">·</span>
                    <span>{CAUSE_CATEGORY[cause.category].label}</span>
                  </span>
                </Link>
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatInteger(cause.run_count)}
              </TableCell>
              <TableCell className="text-right text-muted-foreground tabular-nums">
                {cause.verified_count}/{cause.run_count}
              </TableCell>
              <TableCell className="text-right text-muted-foreground">
                {formatRelative(cause.last_seen_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {causes.hasNextPage && (
        <div className="border-t p-2">
          <LoadMoreButton
            hasNextPage={causes.hasNextPage}
            isFetchingNextPage={causes.isFetchingNextPage}
            onLoadMore={() => causes.fetchNextPage()}
          />
        </div>
      )}
    </div>
  );
}
