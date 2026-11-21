"use client";

import { ChevronDownIcon } from "lucide-react";
import { useEffect, useRef } from "react";

import type { Step } from "@/api/generated";
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

// Every step of the run, top to bottom. Click a step to read it in full.
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
        {isLive ? "Waiting for the first step..." : "This run recorded no steps."}
      </p>
    );
  }

  return (
    <ol className="flex flex-col divide-y" aria-label="Steps of this run">
      {steps.map((step) => {
        const isOpen = step.index === selectedStep;
        const isDomino = step.index === dominoStep;
        return (
          <li key={step.id} id={`step-${step.index}`} className="scroll-mt-20">
            <button
              type="button"
              aria-expanded={isOpen}
              onClick={() => onSelectStep(isOpen ? null : step.index)}
              className={cn(
                "flex w-full items-center gap-3 px-4 py-2.5 text-left outline-none hover:bg-muted/40 focus-visible:bg-muted/40",
                isOpen && "bg-muted/30"
              )}
            >
              <span
                className={cn(
                  "flex h-7 w-6 shrink-0 items-center justify-center rounded border font-mono text-[11px]",
                  isDomino
                    ? "-rotate-6 border-domino bg-domino text-domino-foreground"
                    : "border-border bg-muted/40 text-muted-foreground"
                )}
              >
                {step.index}
              </span>
              <span className="min-w-0 flex-1 truncate font-mono text-xs">
                {stepSummary(step.output)}
              </span>
              <span className="hidden shrink-0 font-mono text-[11px] text-muted-foreground sm:inline">
                {isModelCall(step)
                  ? `${formatInteger(step.tokens_in + step.tokens_out)} tok · ${formatInteger(step.latency_ms)} ms`
                  : "set by replay"}
              </span>
              <ChevronDownIcon
                className={cn(
                  "size-4 shrink-0 text-muted-foreground transition-transform",
                  isOpen && "rotate-180"
                )}
                aria-hidden="true"
              />
            </button>
            {isOpen && (
              <div className="border-t bg-background/40">
                <StepDetail step={step} />
              </div>
            )}
          </li>
        );
      })}
      {isLive && (
        <li ref={endRef} className="flex items-center gap-3 px-4 py-3 text-xs text-search-range">
          <span className="relative flex size-2" aria-hidden="true">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-current opacity-75 motion-reduce:animate-none" />
            <span className="relative inline-flex size-2 rounded-full bg-current" />
          </span>
          Recording... new steps appear here as the agent takes them
        </li>
      )}
    </ol>
  );
}
