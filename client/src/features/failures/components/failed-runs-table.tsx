"use client";

import { ChevronRightIcon, InboxIcon } from "lucide-react";
import Link from "next/link";

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
import { useListRuns } from "@/hooks/api/use-list-runs";
import { formatInteger, formatRelative } from "@/lib/format";
import { pageItems } from "@/lib/paging";

import { FAILED_RUNS } from "../inbox-filters";
import { RunDiagnosisCell, RunVerdictCell } from "./run-diagnosis-cell";

export function FailedRunsTable() {
  const runs = useListRuns(FAILED_RUNS);
  if (runs.isError) {
    return (
      <div className="p-4">
        <QueryError
          error={runs.error}
          what="failed runs"
          source="failures.load_runs"
          onRetry={runs.refetch}
        />
      </div>
    );
  }
  if (runs.isPending) {
    return (
      <div className="flex flex-col gap-3 p-4" aria-busy="true">
        {[0, 1, 2, 3].map((row) => (
          <Skeleton key={row} className="h-11 w-full" />
        ))}
      </div>
    );
  }
  const items = pageItems(runs.data);
  if (items.length === 0) {
    return (
      <EmptyState
        icon={InboxIcon}
        title="No failed runs yet"
        description="Record your agent's runs with the SDK. When your success check marks a run failed, it lands here and is diagnosed automatically."
        action={
          <Link href="/settings" className={buttonVariants({ variant: "brand" })}>
            Connect your agent
          </Link>
        }
      />
    );
  }
  return (
    <div className="flex flex-col">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Run</TableHead>
            <TableHead>First domino</TableHead>
            <TableHead>Verdict</TableHead>
            <TableHead className="text-right">Steps</TableHead>
            <TableHead className="text-right">When</TableHead>
            <TableHead className="w-8">
              <span className="sr-only">Open</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((run) => (
            <TableRow key={run.id} className="group">
              <TableCell className="max-w-[16rem]">
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
              <TableCell className="max-w-[22rem]">
                <RunDiagnosisCell diagnosisId={run.latest_diagnosis_id} />
              </TableCell>
              <TableCell>
                <RunVerdictCell diagnosisId={run.latest_diagnosis_id} />
              </TableCell>
              <TableCell className="text-right font-mono text-xs text-muted-foreground tabular-nums">
                {formatInteger(run.step_count)}
              </TableCell>
              <TableCell className="text-right text-xs whitespace-nowrap text-muted-foreground">
                {formatRelative(run.started_at)}
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
            onLoadMore={() => runs.fetchNextPage()}
          />
        </div>
      )}
    </div>
  );
}
