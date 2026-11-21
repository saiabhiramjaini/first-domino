"use client";

import Link from "next/link";

import { EmptyState } from "@/components/feedback/empty-state";
import { LoadMoreButton } from "@/components/feedback/load-more-button";
import { QueryError } from "@/components/feedback/query-error";
import { shortId } from "@/components/runs/short-id";
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

export function FailedRunsTable() {
  const runs = useListRuns(FAILED_RUNS);
  if (runs.isError) {
    return (
      <QueryError
        error={runs.error}
        what="failed runs"
        source="failures.load_runs"
        onRetry={runs.refetch}
      />
    );
  }
  if (runs.isPending) {
    return (
      <div className="flex flex-col gap-2" aria-busy="true">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }
  const items = pageItems(runs.data);
  if (items.length === 0) {
    return (
      <EmptyState
        title="No failed runs yet"
        description="Record a run with the SDK. When your success check marks it failed, it shows up here and is diagnosed automatically."
      />
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Run</TableHead>
            <TableHead>Task</TableHead>
            <TableHead className="text-right">Steps</TableHead>
            <TableHead>Diagnosis</TableHead>
            <TableHead className="text-right">Started</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((run) => (
            <TableRow key={run.id}>
              <TableCell>
                <Link
                  href={`/runs/${run.id}`}
                  className="flex flex-col font-medium underline-offset-4 hover:underline"
                >
                  {run.agent_name}
                  <span className="font-mono text-xs text-muted-foreground">{shortId(run.id)}</span>
                </Link>
              </TableCell>
              <TableCell className="max-w-xs truncate text-muted-foreground">
                {run.task_input.prompt}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatInteger(run.step_count)}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {run.latest_diagnosis_id ? "Diagnosed" : "Not yet"}
              </TableCell>
              <TableCell className="text-right whitespace-nowrap text-muted-foreground">
                {formatRelative(run.started_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <LoadMoreButton
        hasNextPage={runs.hasNextPage}
        isFetchingNextPage={runs.isFetchingNextPage}
        onLoadMore={() => runs.fetchNextPage()}
      />
    </div>
  );
}
