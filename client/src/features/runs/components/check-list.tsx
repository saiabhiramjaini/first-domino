import type { CheckPhase } from "@/api/generated";
import { StatusBadge } from "@/components/status/status-badge";
import { CHECK_PHASE } from "@/components/status/status-tones";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { driftText } from "../replay-drift";
import { checkResultStatus, type CheckRow } from "./check-rows";

type CheckListProps = {
  checks: CheckRow[];
  selectedCheckId: string | null;
  onViewReplays: (check: CheckRow) => void;
};

export function savePointText(phase: CheckPhase, savePoint: number): string {
  if (phase === "calibrate" && savePoint > 0) {
    return savePoint === 1 ? "Keep the only step" : `Keep all ${savePoint} steps`;
  }
  const kept =
    savePoint === 0
      ? "Fresh run"
      : savePoint === 1
        ? "Keep step 1"
        : `Keep steps 1 to ${savePoint}`;
  if (phase === "verify" || phase === "fallback") {
    return savePoint === 0 ? "Fixed step 1" : `${kept}, then fixed step ${savePoint + 1}`;
  }
  return kept;
}

export function CheckList({ checks, selectedCheckId, onViewReplays }: CheckListProps) {
  if (checks.length === 0) {
    return (
      <p className="p-4 text-sm text-muted-foreground">
        No checks yet. Each check replays the run from a save point and appears here when it starts.
      </p>
    );
  }
  return (
    <div className="max-h-[28rem] overflow-y-auto">
      <Table>
        <TableHeader className="sticky top-0 z-10 bg-card">
          <TableRow>
            <TableHead className="w-12">#</TableHead>
            <TableHead>Phase</TableHead>
            <TableHead>Save point</TableHead>
            <TableHead className="text-right">Passed</TableHead>
            <TableHead className="text-right">Result</TableHead>
            <TableHead className="w-24">
              <span className="sr-only">Replays</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {checks.map((check) => (
            <TableRow
              key={check.id}
              data-state={check.id === selectedCheckId ? "selected" : undefined}
            >
              <TableCell className="font-mono text-xs text-muted-foreground tabular-nums">
                {check.number}
              </TableCell>
              <TableCell>
                <StatusBadge status={CHECK_PHASE[check.phase]} dot={false} />
              </TableCell>
              <TableCell className="text-sm">
                {savePointText(check.phase, check.save_point)}
              </TableCell>
              <TableCell className="text-right font-mono text-xs tabular-nums">
                {check.passes}/{check.samples}
                {check.drifted > 0 && (
                  <span className="block text-muted-foreground">{driftText(check)}</span>
                )}
              </TableCell>
              <TableCell className="text-right">
                <StatusBadge status={checkResultStatus(check)} />
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`View the replays of check ${check.number}`}
                  aria-pressed={check.id === selectedCheckId}
                  onClick={() => onViewReplays(check)}
                >
                  Replays
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
