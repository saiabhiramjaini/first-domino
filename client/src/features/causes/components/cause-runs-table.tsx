"use client";

import Link from "next/link";

import { EmptyState } from "@/components/feedback/empty-state";
import { LoadMoreButton } from "@/components/feedback/load-more-button";
import { QueryError } from "@/components/feedback/query-error";
import { StatusBadge } from "@/components/status/status-badge";
import { DIAGNOSIS_STATUS, VERDICT_KIND } from "@/components/status/status-tones";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useListDiagnoses } from "@/hooks/api/use-list-diagnoses";
import { formatRelative, formatUsd } from "@/lib/format";
import { pageItems } from "@/lib/paging";

import { shortId, verifyPassesLabel } from "../cause-stats";

type CauseRunsTableProps = { causeId: string };

export function CauseRunsTable({ causeId }: CauseRunsTableProps) {
  const diagnoses = useListDiagnoses({ cause_ids: [causeId] });

  if (diagnoses.isPending) {
    return (
      <div className="p-4">
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (diagnoses.isLoadingError) {
    return (
      <div className="p-4">
        <QueryError
          error={diagnoses.error}
          what="the runs of this cause"
          source="causes.list_runs"
          onRetry={() => diagnoses.refetch()}
        />
      </div>
    );
  }

  const items = pageItems(diagnoses.data);
  if (items.length === 0) {
    return (
      <EmptyState
        title="No runs for this cause yet"
        description="Runs appear here when a diagnosis groups them under this cause."
      />
    );
  }

  return (
    <div className="flex flex-col">
      <div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Run</TableHead>
              <TableHead>Verdict</TableHead>
              <TableHead className="text-right">First domino</TableHead>
              <TableHead className="text-right">Fix replays passed</TableHead>
              <TableHead className="text-right">Cost</TableHead>
              <TableHead>Diagnosed</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((diagnosis) => (
              <TableRow key={diagnosis.id}>
                <TableCell>
                  <Link
                    href={`/runs/${diagnosis.run_id}`}
                    className="font-mono text-sm underline-offset-4 hover:underline"
                  >
                    {shortId(diagnosis.run_id)}
                  </Link>
                </TableCell>
                <TableCell>
                  <StatusBadge
                    status={
                      diagnosis.verdict_kind
                        ? VERDICT_KIND[diagnosis.verdict_kind]
                        : DIAGNOSIS_STATUS[diagnosis.status]
                    }
                  />
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {diagnosis.first_domino_step === null
                    ? "None"
                    : `Step ${diagnosis.first_domino_step}`}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {verifyPassesLabel(diagnosis.verify_passes, diagnosis.verify_samples)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatUsd(diagnosis.cost_usd)}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatRelative(diagnosis.created_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <LoadMoreButton
        hasNextPage={diagnoses.hasNextPage}
        isFetchingNextPage={diagnoses.isFetchingNextPage}
        onLoadMore={() => diagnoses.fetchNextPage()}
      />
    </div>
  );
}
