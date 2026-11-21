"use client";

import { ActivityIcon, ChevronRightIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import type { RunStatus } from "@/api/generated";
import { EmptyState } from "@/components/feedback/empty-state";
import { LoadMoreButton } from "@/components/feedback/load-more-button";
import { QueryError } from "@/components/feedback/query-error";
import { Panel } from "@/components/layout/panel";
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
import { RunDiagnosisCell } from "@/features/failures/components/run-diagnosis-cell";
import { useCountRuns } from "@/hooks/api/use-count-runs";
import { useListRuns } from "@/hooks/api/use-list-runs";
import { formatInteger, formatRelative } from "@/lib/format";
import { useNow } from "@/hooks/use-now";
import { pageItems } from "@/lib/paging";
import { cn } from "@/lib/utils";

import { runDuration } from "./run-duration";
import { RunStatusBadge } from "./run-status-badge";

// New runs and status changes show up without a reload.
const LIST_REFRESH_MS = 2_000;

type Filter = "all" | RunStatus;

const FILTERS: ReadonlyArray<{ value: Filter; label: string }> = [
  { value: "all", label: "All" },
  { value: "running", label: "Running" },
  { value: "failed", label: "Failed" },
  { value: "passed", label: "Passed" },
  { value: "errored", label: "Errored" },
];

function statusesOf(filter: Filter): RunStatus[] | undefined {
  return filter === "all" ? undefined : [filter];
}

function FilterChip({
  filter,
  label,
  isActive,
  onSelect,
}: {
  filter: Filter;
  label: string;
  isActive: boolean;
  onSelect: (filter: Filter) => void;
}) {
  const count = useCountRuns(
    { sources: ["recorded"], statuses: statusesOf(filter) },
    { refreshMs: LIST_REFRESH_MS }
  );
  return (
    <button
      type="button"
      aria-pressed={isActive}
      onClick={() => onSelect(filter)}
      className={cn(
        "inline-flex h-8 items-center gap-2 rounded-lg border px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
        isActive
          ? "border-foreground/20 bg-muted text-foreground"
          : "border-transparent text-muted-foreground hover:bg-muted/60 hover:text-foreground"
      )}
    >
      {label}
      <span className="font-mono text-xs text-muted-foreground tabular-nums">
        {count.data === undefined ? "·" : formatInteger(count.data)}
      </span>
    </button>
  );
}

export function RunsList() {
  const [filter, setFilter] = useState<Filter>("all");
  const runs = useListRuns(
    { sources: ["recorded"], statuses: statusesOf(filter) },
    { refreshMs: LIST_REFRESH_MS }
  );
  const now = useNow(LIST_REFRESH_MS);

  return (
    <Panel
      title="All runs"
      description="Every run your agent records, passed or failed, as it happens. Newest first."
      actions={
        <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="size-1.5 rounded-full bg-verified" aria-hidden="true" />
          Live
        </span>
      }
    >
      <div
        className="flex flex-wrap gap-1 border-b px-3 py-2"
        role="group"
        aria-label="Filter by status"
      >
        {FILTERS.map((item) => (
          <FilterChip
            key={item.value}
            filter={item.value}
            label={item.label}
            isActive={filter === item.value}
            onSelect={setFilter}
          />
        ))}
      </div>
      {runs.isError ? (
        <div className="p-4">
          <QueryError
            error={runs.error}
            what="runs"
            source="runs.list"
            onRetry={() => void runs.refetch()}
          />
        </div>
      ) : runs.isPending ? (
        <div className="flex flex-col gap-3 p-4" aria-busy="true">
          {[0, 1, 2, 3].map((row) => (
            <Skeleton key={row} className="h-11 w-full" />
          ))}
        </div>
      ) : pageItems(runs.data).length === 0 ? (
        <EmptyState
          icon={ActivityIcon}
          title={filter === "all" ? "No runs yet" : "No runs with this status"}
          description="Record your agent's runs with the SDK. Each run appears here the moment it starts, and its steps fill in live."
          action={
            filter === "all" && (
              <Link href="/settings" className={buttonVariants({ variant: "brand" })}>
                Connect your agent
              </Link>
            )
          }
        />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Status</TableHead>
                <TableHead>Run</TableHead>
                <TableHead className="text-right">Steps</TableHead>
                <TableHead>First domino</TableHead>
                <TableHead className="text-right">Duration</TableHead>
                <TableHead className="text-right">Started</TableHead>
                <TableHead className="w-8">
                  <span className="sr-only">Open</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pageItems(runs.data).map((run) => (
                <TableRow key={run.id} className="group">
                  <TableCell>
                    <RunStatusBadge status={run.status} />
                  </TableCell>
                  <TableCell className="max-w-[18rem]">
                    <Link
                      href={`/runs/${run.id}`}
                      className="flex min-w-0 flex-col gap-0.5 rounded-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                    >
                      <span className="flex items-center gap-2 font-medium">
                        {run.agent_name}
                        <span className="font-mono text-xs font-normal text-muted-foreground">
                          {shortId(run.id)}
                        </span>
                      </span>
                      <span
                        className="truncate text-xs text-muted-foreground"
                        title={run.task_input.prompt}
                      >
                        {run.task_input.prompt}
                      </span>
                    </Link>
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs tabular-nums">
                    {formatInteger(run.step_count)}
                  </TableCell>
                  <TableCell className="max-w-[18rem]">
                    {run.status === "failed" ? (
                      <RunDiagnosisCell diagnosisId={run.latest_diagnosis_id} />
                    ) : (
                      <span className="text-xs text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs text-muted-foreground tabular-nums">
                    {runDuration(run.started_at, run.finished_at, now)}
                  </TableCell>
                  <TableCell className="text-right text-xs whitespace-nowrap text-muted-foreground">
                    {formatRelative(run.started_at, now)}
                  </TableCell>
                  <TableCell className="pr-3">
                    <Link
                      href={`/runs/${run.id}`}
                      aria-label={`Open run ${shortId(run.id)}`}
                      className="flex size-6 items-center justify-center rounded-md text-muted-foreground opacity-60 outline-none group-hover:opacity-100 hover:bg-muted hover:text-foreground focus-visible:opacity-100 focus-visible:ring-3 focus-visible:ring-ring/50"
                    >
                      <ChevronRightIcon className="size-4" aria-hidden="true" />
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {runs.hasNextPage && (
            <div className="border-t p-3">
              <LoadMoreButton
                hasNextPage={runs.hasNextPage}
                isFetchingNextPage={runs.isFetchingNextPage}
                onLoadMore={() => void runs.fetchNextPage()}
              />
            </div>
          )}
        </>
      )}
    </Panel>
  );
}
