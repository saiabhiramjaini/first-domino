import { ArrowRightIcon, CheckIcon } from "lucide-react";
import Link from "next/link";

import type { Diagnosis, Step } from "@/api/generated";
import { Panel } from "@/components/layout/panel";
import { MessageView } from "@/components/runs/message-view";
import { CAUSE_CATEGORY } from "@/components/status/status-tones";
import { buttonVariants } from "@/components/ui/button";

type VerdictCardProps = { diagnosis: Diagnosis; originalStep: Step | undefined };

function Column({
  label,
  note,
  children,
}: {
  label: React.ReactNode;
  note: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-w-0 flex-col overflow-hidden rounded-md border">
      <div className="flex items-center justify-between gap-3 border-b px-3 py-2 text-xs">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">{note}</span>
      </div>
      <div className="p-3">{children}</div>
    </div>
  );
}

// The evidence: what went wrong, and the recorded step next to the fix that made the run pass.
export function VerdictCard({ diagnosis, originalStep }: VerdictCardProps) {
  const explanation = diagnosis.explanation;
  const domino = diagnosis.first_domino_step;
  if (!explanation && domino === null) return null;
  const proven =
    diagnosis.verify_passes !== null && diagnosis.verify_samples !== null
      ? `passed ${diagnosis.verify_passes} of ${diagnosis.verify_samples} replays`
      : "rewrite";
  return (
    <Panel
      id="proof"
      title="What went wrong"
      description={explanation ? CAUSE_CATEGORY[explanation.category].label : undefined}
      actions={
        diagnosis.cause_id && (
          <Link
            href={`/causes/${diagnosis.cause_id}`}
            className={buttonVariants({ variant: "ghost", size: "sm" })}
          >
            Root cause
            <ArrowRightIcon aria-hidden="true" />
          </Link>
        )
      }
    >
      <div className="flex flex-col gap-5 p-4">
        {explanation && (
          <p className="max-w-3xl text-sm text-pretty whitespace-pre-wrap">{explanation.summary}</p>
        )}
        {domino !== null && (
          <div className="grid gap-3 lg:grid-cols-2">
            <Column
              label={
                <span className="inline-flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-destructive" aria-hidden="true" />
                  Recorded step {domino}
                </span>
              }
              note="failed the run"
            >
              {originalStep ? (
                <MessageView message={originalStep.output} />
              ) : (
                <p className="text-sm text-muted-foreground">Loading the recorded step…</p>
              )}
            </Column>
            <Column
              label={
                <span className="inline-flex items-center gap-1.5">
                  <CheckIcon className="size-3.5" aria-hidden="true" />
                  Fixed step {domino}
                </span>
              }
              note={proven}
            >
              {diagnosis.fixed_output ? (
                <MessageView message={diagnosis.fixed_output} />
              ) : (
                <p className="text-sm text-muted-foreground">No fix was written for this step.</p>
              )}
            </Column>
          </div>
        )}
        {explanation && (
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Suggested fix</span>
            <p className="max-w-3xl text-sm text-pretty whitespace-pre-wrap">
              {explanation.suggested_fix}
            </p>
          </div>
        )}
      </div>
    </Panel>
  );
}
