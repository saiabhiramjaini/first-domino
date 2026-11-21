"use client";

import { useEffect, useRef } from "react";

import type { Step } from "@/api/generated";
import { Button } from "@/components/ui/button";
import { formatInteger } from "@/lib/format";
import { cn } from "@/lib/utils";

import { stepSummary } from "../trace-summary";
import { StepDetail, isModelCall } from "./step-detail";

type RunTraceProps = {
  steps: Step[];
  selectedStep: number | null;
  dominoStep: number | null;
  isLive: boolean;
  onSelectStep: (step: number | null) => void;
};

// Every step on the left; the picked step in full on the right. On a phone they stack.
export function RunTrace({ steps, selectedStep, dominoStep, isLive, onSelectStep }: RunTraceProps) {
  const endRef = useRef<HTMLLIElement>(null);
  const count = steps.length;

  useEffect(() => {
    if (isLive && count > 0)
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [isLive, count]);

  if (count === 0) {
    return (
      <p className="p-4 text-sm text-muted-foreground">
        {isLive ? "Waiting for the first step…" : "This run recorded no steps."}
      </p>
    );
  }

  const shown = steps.find((step) => step.index === selectedStep) ?? steps.at(-1);
  return (
    <div className="grid min-h-80 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
      <ol
        className="flex max-h-[36rem] flex-col overflow-y-auto border-b lg:border-r lg:border-b-0"
        aria-label="Steps of this run"
      >
        {steps.map((step) => {
          const isShown = step.index === shown?.index;
          const isDomino = step.index === dominoStep;
          return (
            <li key={step.id} id={`step-${step.index}`} className="scroll-mt-20">
              <Button
                variant="ghost"
                aria-pressed={isShown}
                onClick={() => onSelectStep(step.index)}
                className={cn(
                  "h-auto w-full justify-start gap-3 rounded-none px-3 py-2.5 text-left font-normal",
                  isShown && "bg-muted"
                )}
              >
                <span
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded font-mono text-xs",
                    isDomino
                      ? "-rotate-6 bg-domino text-domino-foreground"
                      : "bg-muted text-muted-foreground"
                  )}
                >
                  {step.index}
                </span>
                <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span className="truncate font-mono text-xs">{stepSummary(step.output)}</span>
                  <span className="text-xs text-muted-foreground">
                    {isDomino && <span className="text-domino">First domino · </span>}
                    {isModelCall(step)
                      ? `${formatInteger(step.latency_ms)} ms · ${formatInteger(step.tokens_in + step.tokens_out)} tokens`
                      : "Set by a replay"}
                  </span>
                </span>
              </Button>
            </li>
          );
        })}
        {isLive && (
          <li
            ref={endRef}
            className="flex items-center gap-2.5 px-3 py-3 text-xs text-muted-foreground"
          >
            <span className="relative flex size-1.5" aria-hidden="true">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-foreground opacity-60 motion-reduce:animate-none" />
              <span className="relative inline-flex size-1.5 rounded-full bg-foreground" />
            </span>
            Recording…
          </li>
        )}
      </ol>
      <div className="min-w-0">
        {shown && <StepDetail step={shown} isDomino={shown.index === dominoStep} />}
      </div>
    </div>
  );
}
