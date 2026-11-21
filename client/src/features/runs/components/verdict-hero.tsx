"use client";

import { PlugZapIcon } from "lucide-react";
import Link from "next/link";

import type { Diagnosis } from "@/api/generated";
import { StatusBadge } from "@/components/status/status-badge";
import { buttonVariants } from "@/components/ui/button";
import { DIAGNOSIS_STATUS, VERDICT_KIND } from "@/components/status/status-tones";
import { isDiagnosisActive } from "@/hooks/api/diagnosis-activity";
import { formatInteger, formatUsd } from "@/lib/format";
import { cn } from "@/lib/utils";

import { useNow } from "@/hooks/use-now";

import { verdictCopy } from "../verdict-copy";
import { isWaitingForWorker, waitedText, workerWaitMs } from "../worker-wait";

const CLOCK_MS = 1_000;

type VerdictHeroProps = { diagnosis: Diagnosis; children: React.ReactNode };

function liveText(diagnosis: Diagnosis): string {
  const { search_low: low, search_high: high, status } = diagnosis;
  if (status === "queued") return "Waiting for your replay worker to pick up the first check.";
  if (status === "verifying") return "Rewriting the found step and replaying to prove it.";
  if (status === "explaining") return "Writing up what went wrong.";
  if (low === null || high === null) return "Checking whether a fresh run can succeed at all.";
  if (low === high) return `Narrowed to step ${low}.`;
  if (low === 0)
    return `Checking the whole run: the first domino is somewhere in steps 1 to ${high}.`;
  return `The first domino is between step ${low} and step ${high}.`;
}

function Stat({ label, value, isDomino }: { label: string; value: string; isDomino?: boolean }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("text-sm font-medium tabular-nums", isDomino && "text-domino")}>{value}</dd>
    </div>
  );
}

// The answer first: where the run fell, how sure we are, and what it cost. The step strip sits below.
export function VerdictHero({ diagnosis, children }: VerdictHeroProps) {
  const isActive = isDiagnosisActive(diagnosis.status);
  const now = useNow(isActive ? CLOCK_MS : false);
  const isWaiting = isWaitingForWorker(diagnosis, now);
  const waited = workerWaitMs(diagnosis, now) ?? 0;
  const copy = diagnosis.status === "done" ? verdictCopy(diagnosis) : null;
  const proof =
    diagnosis.verify_passes !== null && diagnosis.verify_samples !== null
      ? `${diagnosis.verify_passes}/${diagnosis.verify_samples}`
      : "–";
  const verdict = diagnosis.verdict_kind;
  return (
    <section aria-labelledby="verdict-title" className="rounded-lg border">
      <div className="flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
          {verdict && diagnosis.status === "done" ? (
            <StatusBadge
              status={{
                tone: diagnosis.first_domino_step === null ? "neutral" : "domino",
                label: VERDICT_KIND[verdict].label,
              }}
            />
          ) : isWaiting ? (
            <StatusBadge status={{ tone: "warning", label: "Waiting for your replay worker" }} />
          ) : (
            <StatusBadge
              status={{
                tone: isActive ? "info" : "neutral",
                label: DIAGNOSIS_STATUS[diagnosis.status].label,
              }}
            />
          )}
          <dl className="flex flex-wrap gap-x-5 gap-y-1">
            <Stat
              label="First domino"
              value={diagnosis.first_domino_step === null ? "–" : `#${diagnosis.first_domino_step}`}
              isDomino={diagnosis.first_domino_step !== null}
            />
            <Stat label="Proof" value={proof} />
            <Stat label="Replays" value={formatInteger(diagnosis.replay_count)} />
            <Stat label="Cost" value={formatUsd(diagnosis.cost_usd)} />
          </dl>
        </div>
        <div className="flex flex-col gap-1.5">
          <h2 id="verdict-title" className="text-lg font-semibold tracking-tight text-balance">
            {copy?.headline ??
              (isWaiting
                ? "Waiting for your replay worker"
                : isActive
                  ? "Searching for the first domino"
                  : "Diagnosis")}
          </h2>
          <p className="max-w-3xl text-sm text-pretty text-muted-foreground" aria-live="polite">
            {isWaiting
              ? `${diagnosis.replays_waiting ?? 0} replays have waited ${waitedText(waited)} and no worker has picked them up. Replays run on your side, so start the replay worker next to your agent. The search carries on as soon as it connects.`
              : (copy?.body ?? (isActive ? liveText(diagnosis) : ""))}
          </p>
        </div>
        {isWaiting && (
          <Link
            href="/settings#start_worker"
            className={buttonVariants({ variant: "outline", size: "sm", className: "self-start" })}
          >
            <PlugZapIcon aria-hidden="true" />
            Set up the replay worker
          </Link>
        )}
      </div>
      <div className="border-t px-5 py-4">{children}</div>
    </section>
  );
}
