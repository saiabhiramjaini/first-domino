import type { Check, CheckPhase } from "@/api/generated";
import { StatusBadge } from "@/components/status/status-badge";
import { CHECK_PHASE, CHECK_RESULT } from "@/components/status/status-tones";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type CheckListProps = {
  checks: Check[];
  selectedCheckId: string | null;
  onViewReplays: (check: Check) => void;
};

export function savePointText(phase: CheckPhase, savePoint: number): string {
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
      <p className="text-sm text-muted-foreground">
        No checks yet. Each check replays the run from a save point and appears here when it starts.
      </p>
    );
  }
  return (
    <div className="max-h-96 overflow-y-auto rounded-xl border">
      <Table>
        <TableHeader className="sticky top-0 bg-card">
          <TableRow>
            <TableHead className="w-12">#</TableHead>
            <TableHead>Phase</TableHead>
            <TableHead>Save point</TableHead>
            <TableHead className="text-right">Passed</TableHead>
            <TableHead className="text-right">Result</TableHead>
            <TableHead className="w-28">
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
              <TableCell className="text-muted-foreground tabular-nums">{check.index}</TableCell>
              <TableCell>
                <StatusBadge status={CHECK_PHASE[check.phase]} />
              </TableCell>
              <TableCell>{savePointText(check.phase, check.save_point)}</TableCell>
              <TableCell className="text-right tabular-nums">
                {check.passes} of {check.samples}
              </TableCell>
              <TableCell className="text-right">
                <StatusBadge status={CHECK_RESULT[check.result]} />
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`View the replays of check ${check.index}`}
                  aria-pressed={check.id === selectedCheckId}
                  onClick={() => onViewReplays(check)}
                >
                  View replays
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
