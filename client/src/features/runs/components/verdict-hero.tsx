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

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("font-mono text-lg font-medium tabular-nums", tone)}>{value}</dd>
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
      : "-";
  const verdict = diagnosis.verdict_kind;
  return (
    <section
      aria-labelledby="verdict-title"
      className="relative overflow-hidden rounded-xl border bg-card"
    >
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-[radial-gradient(60%_100%_at_0%_0%,color-mix(in_oklch,var(--domino),transparent_86%),transparent)]"
        aria-hidden="true"
      />
      <div className="relative flex flex-col gap-6 p-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {isActive && !isWaiting && (
              <span className="relative flex size-2" aria-hidden="true">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-search-range opacity-75" />
                <span className="relative inline-flex size-2 rounded-full bg-search-range" />
              </span>
            )}
            {verdict && diagnosis.status === "done" ? (
              <StatusBadge status={VERDICT_KIND[verdict]} />
            ) : isWaiting ? (
              <StatusBadge status={{ tone: "warning", label: "Waiting for your worker" }} />
            ) : (
              <StatusBadge status={DIAGNOSIS_STATUS[diagnosis.status]} />
            )}
          </div>
          <h2 id="verdict-title" className="text-xl font-semibold tracking-tight text-balance">
            {copy?.headline ??
              (isWaiting
                ? "Waiting for your replay worker"
                : isActive
                  ? "Searching for the first domino"
                  : "Diagnosis")}
          </h2>
          <p className="max-w-2xl text-sm text-pretty text-muted-foreground" aria-live="polite">
            {isWaiting
              ? `${diagnosis.replays_waiting ?? 0} replays have been waiting ${waitedText(waited)} and no worker has picked them up. Replays run on your side, so start the replay worker next to your agent. The search carries on by itself as soon as it connects.`
              : (copy?.body ?? (isActive ? liveText(diagnosis) : ""))}
          </p>
          {isWaiting && (
            <Link
              href="/settings#start_worker"
              className={buttonVariants({
                variant: "outline",
                size: "sm",
                className: "self-start",
              })}
            >
              <PlugZapIcon aria-hidden="true" />
              Set up the replay worker
            </Link>
          )}
        </div>
        <dl className="grid shrink-0 grid-cols-4 gap-x-6 gap-y-3 rounded-lg border bg-background/50 px-4 py-3">
          <Stat
            label="First domino"
            value={diagnosis.first_domino_step === null ? "-" : `#${diagnosis.first_domino_step}`}
            tone="text-domino"
          />
          <Stat
            label="Proof"
            value={proof}
            tone={verdict === "step_verified" ? "text-verified" : undefined}
          />
          <Stat label="Replays" value={formatInteger(diagnosis.replay_count)} />
          <Stat label="Cost" value={formatUsd(diagnosis.cost_usd)} />
        </dl>
      </div>
      <div className="relative border-t px-5 py-5">{children}</div>
    </section>
  );
}
