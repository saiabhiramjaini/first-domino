"use client";

import { ArrowUpRightIcon } from "lucide-react";
import Link from "next/link";

import type { Check, Diagnosis, Run } from "@/api/generated";
import { MessageView } from "@/components/runs/message-view";
import { shortId } from "@/components/runs/short-id";
import { Skeleton } from "@/components/ui/skeleton";
import { useListRuns } from "@/hooks/api/use-list-runs";
import { useListSteps } from "@/hooks/api/use-list-steps";
import { pageItems } from "@/lib/paging";

import { stepSummary } from "../trace-summary";
import { provingCheck } from "./proving-check";

type AfterTheFixProps = { diagnosis: Diagnosis; checks: readonly Check[] };

// What the agent did once the fixed step was swapped in: the rest of one passing replay, up to
// its final answer. The recorded run never changes; this is where the fix shows its effect.
export function AfterTheFix({ diagnosis, checks }: AfterTheFixProps) {
  const domino = diagnosis.first_domino_step;
  const check = provingCheck(checks, domino);
  if (!check || domino === null) return null;
  return <PassingReplay check={check} domino={domino} />;
}

function PassingReplay({ check, domino }: { check: Check; domino: number }) {
  const replays = useListRuns({ check_id: check.id });
  if (replays.isPending) return <Skeleton className="h-28 w-full" />;
  const passed = pageItems(replays.data).find((run) => run.status === "passed");
  return passed ? <ReplayTail run={passed} domino={domino} /> : null;
}

function ReplayTail({ run, domino }: { run: Run; domino: number }) {
  const steps = useListSteps(run.id);
  if (!steps.data) return <Skeleton className="h-28 w-full" />;
  const after = steps.data.filter((step) => step.index > domino);
  const last = after.at(-1);
  const lastIsText = last !== undefined && (last.output.tool_calls ?? []).length === 0;

  return (
    <section
      aria-labelledby="after-the-fix-title"
      className="flex flex-col overflow-hidden rounded-md border"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-3 py-2 text-xs">
        <h4 id="after-the-fix-title" className="font-medium">
          After the fix
        </h4>
        <Link
          href={`/runs/${run.id}`}
          className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
        >
          Replay {shortId(run.id)} · passed your check
          <ArrowUpRightIcon className="size-3.5" aria-hidden="true" />
        </Link>
      </div>
      <div className="flex flex-col gap-3 p-3">
        <p className="text-sm text-muted-foreground">
          With the fixed step {domino}, your agent carried on by itself:
        </p>
        {after.length === 0 ? (
          <p className="text-sm text-muted-foreground">The fixed step was its last step.</p>
        ) : (
          <ol className="flex flex-col gap-1.5" aria-label="Steps after the fix">
            {after.map((step) => (
              <li key={step.id} className="flex items-baseline gap-3">
                <span className="w-12 shrink-0 text-xs text-muted-foreground tabular-nums">
                  Step {step.index}
                </span>
                <span className="min-w-0 truncate font-mono text-xs">
                  {stepSummary(step.output)}
                </span>
              </li>
            ))}
          </ol>
        )}
        {lastIsText && <MessageView message={last.output} />}
      </div>
    </section>
  );
}
