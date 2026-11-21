import Link from "next/link";

import type { Check, Run, Step } from "@/api/generated";
import { StatusBadge } from "@/components/status/status-badge";
import { CHECK_PHASE, CHECK_RESULT, RUN_STATUS } from "@/components/status/status-tones";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

import { savePointText } from "../components/check-list";
import { comparedStepIndices, divergenceStep, stepsByIndex } from "./divergence";
import { StepCell } from "./step-cell";

export type ReplayLane = { run: Run; steps: Step[] };

type ReplayComparisonProps = {
  check: Check;
  originalSteps: Step[];
  replays: ReplayLane[];
};

function isFixCheck(check: Check): boolean {
  return check.phase === "verify" || check.phase === "fallback";
}

export function ReplayComparison({ check, originalSteps, replays }: ReplayComparisonProps) {
  const savePoint = check.save_point;
  const rewrittenStep = isFixCheck(check) ? savePoint + 1 : null;
  const rows = comparedStepIndices(
    [originalSteps, ...replays.map((lane) => lane.steps)],
    savePoint
  );
  const original = stepsByIndex(originalSteps);
  const lanes = replays.map((lane, position) => ({
    ...lane,
    label: `Replay ${position + 1}`,
    byIndex: stepsByIndex(lane.steps),
    divergence: divergenceStep(originalSteps, lane.steps, savePoint),
  }));
  const passed = replays.filter((lane) => lane.run.status === "passed").length;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={CHECK_PHASE[check.phase]} dot={false} />
        <span className="text-sm font-medium">{savePointText(check.phase, savePoint)}</span>
        <StatusBadge status={CHECK_RESULT[check.result]} />
        <span className="font-mono text-xs text-muted-foreground">
          {passed}/{replays.length} replays passed
        </span>
      </div>
      <p className="text-sm text-muted-foreground">
        {savePoint === 0
          ? "Every replay starts again from the task."
          : `Steps 1 to ${savePoint} are kept exactly as recorded in every replay.`}{" "}
        A highlighted cell is where that replay first does something different.
      </p>

      <div className="overflow-hidden rounded-lg border">
        <Table className="min-w-max">
          <TableHeader>
            <TableRow className="bg-muted/30 hover:bg-muted/30">
              <TableHead className="w-16 text-xs">Step</TableHead>
              <TableHead className="h-auto w-64 py-3 align-top whitespace-normal">
                <div className="flex flex-col gap-1">
                  <span className="text-sm font-medium tracking-normal text-foreground normal-case">
                    Original run
                  </span>
                  <span className="text-xs tracking-normal normal-case">As recorded</span>
                </div>
              </TableHead>
              {lanes.map((lane) => (
                <TableHead
                  key={lane.run.id}
                  className="h-auto w-64 py-3 align-top whitespace-normal"
                >
                  <div className="flex flex-col items-start gap-1">
                    <span className="flex items-center gap-2 text-sm font-medium tracking-normal text-foreground normal-case">
                      {lane.label}
                      <StatusBadge status={RUN_STATUS[lane.run.status]} />
                    </span>
                    <Link
                      href={`/runs/${lane.run.id}`}
                      className="text-xs tracking-normal normal-case underline-offset-4 hover:text-foreground hover:underline"
                    >
                      Open this replay
                    </Link>
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((index) => (
              <TableRow key={index} className="hover:bg-transparent">
                <th
                  scope="row"
                  className="p-3 align-top font-mono text-xs text-muted-foreground tabular-nums"
                >
                  {index}
                </th>
                <TableCell className="p-3 align-top whitespace-normal">
                  <StepCell step={original.get(index)} />
                </TableCell>
                {lanes.map((lane) => {
                  const isRewritten = index === rewrittenStep;
                  const isDivergence = index === lane.divergence;
                  return (
                    <TableCell
                      key={lane.run.id}
                      className={cn(
                        "p-3 align-top whitespace-normal",
                        isDivergence && "bg-warning/8",
                        isRewritten && "bg-verified/8"
                      )}
                    >
                      {(isRewritten || isDivergence) && (
                        <Badge variant={isRewritten ? "success" : "warning"} className="mb-1.5">
                          {isRewritten ? "Rewritten step" : "Differs here"}
                        </Badge>
                      )}
                      <StepCell step={lane.byIndex.get(index)} />
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
