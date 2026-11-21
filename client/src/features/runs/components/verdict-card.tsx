import { ArrowRightIcon } from "lucide-react";
import Link from "next/link";

import type { Diagnosis, Step } from "@/api/generated";
import { Panel } from "@/components/layout/panel";
import { MessageView } from "@/components/runs/message-view";
import { StatusBadge } from "@/components/status/status-badge";
import { CAUSE_CATEGORY } from "@/components/status/status-tones";
import { buttonVariants } from "@/components/ui/button";

type VerdictCardProps = { diagnosis: Diagnosis; originalStep: Step | undefined };

// The evidence: what went wrong, the recorded step next to the rewrite that made the run pass.
export function VerdictCard({ diagnosis, originalStep }: VerdictCardProps) {
  const explanation = diagnosis.explanation;
  const domino = diagnosis.first_domino_step;
  if (!explanation && domino === null) return null;
  return (
    <Panel
      id="proof"
      title={explanation?.title ?? "The first domino"}
      description={
        explanation ? (
          <span className="inline-flex items-center gap-2">
            <StatusBadge status={CAUSE_CATEGORY[explanation.category]} dot={false} />
          </span>
        ) : undefined
      }
      actions={
        diagnosis.cause_id && (
          <Link
            href={`/causes/${diagnosis.cause_id}`}
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            Runs with this cause
            <ArrowRightIcon aria-hidden="true" />
          </Link>
        )
      }
    >
      <div className="flex flex-col gap-6 p-4">
        {explanation && (
          <p className="max-w-3xl text-sm text-pretty whitespace-pre-wrap">{explanation.summary}</p>
        )}
        {domino !== null && (
          <div className="grid gap-3 lg:grid-cols-2">
            <div className="flex min-w-0 flex-col overflow-hidden rounded-lg border border-domino/35">
              <div className="flex items-center justify-between border-b border-domino/25 bg-domino/10 px-3 py-2">
                <span className="text-xs font-medium text-domino">Recorded step {domino}</span>
                <span className="font-mono text-[11px] text-domino/80">doomed the run</span>
              </div>
              <div className="p-3">
                {originalStep ? (
                  <MessageView message={originalStep.output} />
                ) : (
                  <p className="text-sm text-muted-foreground">Loading the recorded step...</p>
                )}
              </div>
            </div>
            <div className="flex min-w-0 flex-col overflow-hidden rounded-lg border border-verified/35">
              <div className="flex items-center justify-between border-b border-verified/25 bg-verified/10 px-3 py-2">
                <span className="text-xs font-medium text-verified">Fixed step {domino}</span>
                <span className="font-mono text-[11px] text-verified/80">
                  {diagnosis.verify_passes !== null && diagnosis.verify_samples !== null
                    ? `passed ${diagnosis.verify_passes}/${diagnosis.verify_samples} replays`
                    : "rewrite"}
                </span>
              </div>
              <div className="p-3">
                {diagnosis.fixed_output ? (
                  <MessageView message={diagnosis.fixed_output} />
                ) : (
                  <p className="text-sm text-muted-foreground">No fix was written for this step.</p>
                )}
              </div>
            </div>
          </div>
        )}
        {explanation && (
          <div className="flex flex-col gap-1.5 rounded-lg border bg-background/50 p-4">
            <span className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
              Suggested fix
            </span>
            <p className="text-sm text-pretty whitespace-pre-wrap">{explanation.suggested_fix}</p>
          </div>
        )}
      </div>
    </Panel>
  );
}
