import type { Check, CheckPhase } from "@/api/generated";
import { StatusBadge } from "@/components/status/status-badge";
import { CHECK_PHASE, CHECK_RESULT } from "@/components/status/status-tones";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type CheckListProps = { checks: Check[] };

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

export function CheckList({ checks }: CheckListProps) {
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
          </TableRow>
        </TableHeader>
        <TableBody>
          {checks.map((check) => (
            <TableRow key={check.id}>
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
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
