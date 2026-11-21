"use client";

import { ActivityIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { LoadMoreButton } from "@/components/feedback/load-more-button";
import { QueryError } from "@/components/feedback/query-error";
import { shortId } from "@/components/runs/short-id";
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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RunDiagnosisCell } from "@/features/failures/components/run-diagnosis-cell";
import { useCountRuns } from "@/hooks/api/use-count-runs";
import { useListRuns } from "@/hooks/api/use-list-runs";
import { useNow } from "@/hooks/use-now";
import { formatInteger, formatRelative } from "@/lib/format";
import { pageItems } from "@/lib/paging";

import { RUN_FILTERS, type RunFilter, statusesOf } from "./run-filter";
import { runDuration } from "./run-duration";
import { RunStatusBadge } from "./run-status-badge";

// New runs and status changes show up without a reload.
const LIST_REFRESH_MS = 2_000;
const SKELETON_ROWS = ["a", "b", "c", "d", "e"] as const;

function FilterCount({ filter }: { filter: RunFilter }) {
  const count = useCountRuns(
    { sources: ["recorded"], statuses: statusesOf(filter) },
    { refreshMs: LIST_REFRESH_MS }
  );
  return (
    <span className="text-xs text-muted-foreground tabular-nums">
      {count.data === undefined ? "" : formatInteger(count.data)}
    </span>
  );
}

type RunsListProps = { initialFilter: RunFilter };

export function RunsList({ initialFilter }: RunsListProps) {
  const router = useRouter();
  const [filter, setFilter] = useState<RunFilter>(initialFilter);
  const runs = useListRuns(
    { sources: ["recorded"], statuses: statusesOf(filter) },
    { refreshMs: LIST_REFRESH_MS }
  );
  const now = useNow(LIST_REFRESH_MS);

  function selectFilter(value: RunFilter) {
    setFilter(value);
    router.replace(value === "all" ? "/runs" : `/runs?status=${value}`, { scroll: false });
  }

  const items = runs.data ? pageItems(runs.data) : [];
  return (
    <section aria-label="Runs" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3 border-b">
        <Tabs
          value={filter}
          onValueChange={(value) => selectFilter(value as RunFilter)}
          className="min-w-0 overflow-x-auto"
        >
          <TabsList variant="line" className="h-9 gap-3 p-0">
            {RUN_FILTERS.map((item) => (
              <TabsTrigger key={item.value} value={item.value} className="flex-none px-0.5">
                {item.label}
                <FilterCount filter={item.value} />
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <span className="hidden items-center gap-1.5 text-xs text-muted-foreground sm:inline-flex">
          <span className="relative flex size-1.5" aria-hidden="true">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-foreground opacity-50 motion-reduce:animate-none" />
            <span className="relative inline-flex size-1.5 rounded-full bg-foreground" />
          </span>
          Live
        </span>
      </div>

      {runs.isLoadingError ? (
        <QueryError
          error={runs.error}
          what="runs"
          source="runs.list"
          onRetry={() => void runs.refetch()}
        />
      ) : runs.isPending ? (
        <div className="flex flex-col gap-2" aria-busy="true">
          {SKELETON_ROWS.map((row) => (
            <Skeleton key={row} className="h-10 w-full" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-lg border">
          <EmptyState
            icon={ActivityIcon}
            title={filter === "all" ? "No runs yet" : "No runs here"}
            description={
              filter === "all"
                ? "Add two lines to your agent and every run shows up here the moment it starts, with its steps filling in live."
                : "No recorded run has this status yet."
            }
            action={
              filter === "all" && (
                <Link href="/settings" className={buttonVariants({ variant: "brand" })}>
                  Connect your agent
                </Link>
              )
            }
          />
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-28">Status</TableHead>
                <TableHead>Run</TableHead>
                <TableHead>First domino</TableHead>
                <TableHead className="hidden text-right md:table-cell">Steps</TableHead>
                <TableHead className="hidden text-right md:table-cell">Duration</TableHead>
                <TableHead className="text-right">Started</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((run) => (
                <TableRow
                  key={run.id}
                  className="cursor-pointer"
                  onClick={() => router.push(`/runs/${run.id}`)}
                >
                  <TableCell>
                    <RunStatusBadge status={run.status} />
                  </TableCell>
                  <TableCell className="max-w-[24rem]">
                    <Link
                      href={`/runs/${run.id}`}
                      onClick={(event) => event.stopPropagation()}
                      className="flex min-w-0 flex-col gap-0.5 rounded-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                    >
                      <span className="truncate" title={run.task_input.prompt}>
                        {run.task_input.prompt}
                      </span>
                      <span className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                        {run.agent_name}
                        <span aria-hidden="true">·</span>
                        {shortId(run.id)}
                        {run.flagged_at !== null && (
                          <>
                            <span aria-hidden="true">·</span>
                            <span className="font-sans">Flagged</span>
                          </>
                        )}
                      </span>
                    </Link>
                  </TableCell>
                  <TableCell className="max-w-[20rem]">
                    {run.status === "failed" ? (
                      <RunDiagnosisCell diagnosisId={run.latest_diagnosis_id} />
                    ) : (
                      <span className="text-muted-foreground" aria-label="None">
                        –
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="hidden text-right tabular-nums md:table-cell">
                    {formatInteger(run.step_count)}
                  </TableCell>
                  <TableCell className="hidden text-right text-muted-foreground tabular-nums md:table-cell">
                    {runDuration(run.started_at, run.finished_at, now)}
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap text-muted-foreground">
                    {formatRelative(run.started_at, now)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {runs.hasNextPage && (
            <div className="border-t p-2">
              <LoadMoreButton
                hasNextPage={runs.hasNextPage}
                isFetchingNextPage={runs.isFetchingNextPage}
                onLoadMore={() => void runs.fetchNextPage()}
              />
            </div>
          )}
        </div>
      )}
    </section>
  );
}
