import Link from "next/link";

import type { Diagnosis, Step } from "@/api/generated";
import { MessageView } from "@/components/runs/message-view";
import { StatusBadge } from "@/components/status/status-badge";
import { CAUSE_CATEGORY, VERDICT_KIND } from "@/components/status/status-tones";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { verdictCopy } from "../verdict-copy";

type VerdictCardProps = { diagnosis: Diagnosis; originalStep: Step | undefined };

function verifyText(diagnosis: Diagnosis): string | null {
  if (diagnosis.verify_passes === null || diagnosis.verify_samples === null) return null;
  return `${diagnosis.verify_passes} of ${diagnosis.verify_samples} replays passed with the fixed step`;
}

export function VerdictCard({ diagnosis, originalStep }: VerdictCardProps) {
  const verdict = diagnosis.verdict_kind;
  const explanation = diagnosis.explanation;
  const copy = verdictCopy(diagnosis);
  const verify = verifyText(diagnosis);
  const domino = diagnosis.first_domino_step;
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          {verdict && <StatusBadge status={VERDICT_KIND[verdict]} />}
          {explanation && <StatusBadge status={CAUSE_CATEGORY[explanation.category]} />}
        </div>
        <CardTitle className="text-lg">
          {explanation?.title ?? copy?.headline ?? "Diagnosis finished"}
        </CardTitle>
        {copy && (
          <CardDescription>
            {explanation && <span className="font-medium text-foreground">{copy.headline}. </span>}
            {copy.body}
          </CardDescription>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {explanation && (
          <section className="flex flex-col gap-1">
            <h3 className="text-xs font-medium text-muted-foreground">What went wrong</h3>
            <p className="text-sm whitespace-pre-wrap">{explanation.summary}</p>
          </section>
        )}
        {domino !== null && (
          <div className="grid gap-3 md:grid-cols-2">
            <section className="flex min-w-0 flex-col gap-2 rounded-lg border border-domino/40 bg-domino/5 p-3">
              <h3 className="text-xs font-medium text-domino">Original step {domino}</h3>
              {originalStep ? (
                <MessageView message={originalStep.output} />
              ) : (
                <p className="text-sm text-muted-foreground">Loading the original step...</p>
              )}
            </section>
            <section className="flex min-w-0 flex-col gap-2 rounded-lg border border-verified/40 bg-verified/5 p-3">
              <h3 className="text-xs font-medium text-verified">Fixed step {domino}</h3>
              {diagnosis.fixed_output ? (
                <MessageView message={diagnosis.fixed_output} />
              ) : (
                <p className="text-sm text-muted-foreground">No fix was written for this step.</p>
              )}
            </section>
          </div>
        )}
        {verify && <p className="text-sm font-medium">{verify}</p>}
        {explanation && (
          <div className="flex flex-col gap-1 rounded-lg bg-muted p-3">
            <span className="text-xs font-medium text-muted-foreground">Suggested fix</span>
            <p className="text-sm whitespace-pre-wrap">{explanation.suggested_fix}</p>
          </div>
        )}
        {diagnosis.cause_id && (
          <Link
            href={`/causes/${diagnosis.cause_id}`}
            className={buttonVariants({ variant: "outline", className: "self-start" })}
          >
            See runs with this cause
          </Link>
        )}
      </CardContent>
    </Card>
  );
}
