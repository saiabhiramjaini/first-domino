"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { stepState, type StepState, type StripDiagnosis } from "./step-strip-state";

const STATE_CLASSES = {
  idle: "border-border bg-muted/40 text-muted-foreground",
  in_range: "border-search-range/60 bg-search-range/12 text-search-range",
  ruled_out: "border-transparent bg-ruled-out/60 text-muted-foreground/70",
  first_domino:
    "border-domino bg-domino text-domino-foreground shadow-[0_0_24px_-4px_var(--domino)] -rotate-6",
  verified_domino:
    "border-domino bg-domino text-domino-foreground shadow-[0_0_24px_-4px_var(--domino)] -rotate-6 ring-2 ring-verified ring-offset-2 ring-offset-card",
} as const satisfies Record<StepState, string>;

const STATE_LABELS = {
  idle: "not checked yet",
  in_range: "still in the search range",
  ruled_out: "ruled out",
  first_domino: "the first domino",
  verified_domino: "the first domino, verified by a fix",
} as const satisfies Record<StepState, string>;

const LEGEND: ReadonlyArray<{ state: StepState; label: string }> = [
  { state: "in_range", label: "Search range" },
  { state: "first_domino", label: "First domino" },
  { state: "verified_domino", label: "Verified" },
  { state: "ruled_out", label: "Ruled out" },
];

const TILE_CLASSES =
  "h-12 w-9 rounded-md border font-mono text-xs font-medium tabular-nums transition-[transform,background-color,border-color] duration-300 motion-reduce:transition-none";

function stepNumbers(stepCount: number): number[] {
  return Array.from({ length: stepCount }, (_, offset) => offset + 1);
}

export function StepStripLegend() {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {LEGEND.map((item) => (
        <li key={item.state} className="flex items-center gap-1.5">
          <span className={cn("size-3 rounded-sm border", STATE_CLASSES[item.state])} />
          {item.label}
        </li>
      ))}
    </ul>
  );
}

type RunStepStripProps = {
  stepCount: number;
  diagnosis: StripDiagnosis | undefined;
  selectedStep: number | null;
  onSelectStep: (step: number) => void;
};

export function RunStepStrip({
  stepCount,
  diagnosis,
  selectedStep,
  onSelectStep,
}: RunStepStripProps) {
  return (
    <div className="flex flex-col gap-3">
      <ol className="flex flex-wrap gap-2" aria-label="Steps of this run">
        {stepNumbers(stepCount).map((step) => {
          const state = stepState(step, diagnosis);
          const isSelected = step === selectedStep;
          return (
            <li key={step}>
              <Button
                variant="outline"
                size="icon-lg"
                onClick={() => onSelectStep(step)}
                aria-pressed={isSelected}
                aria-label={`Step ${step}, ${STATE_LABELS[state]}`}
                className={cn(
                  TILE_CLASSES,
                  STATE_CLASSES[state],
                  isSelected && "outline-2 outline-offset-3 outline-foreground"
                )}
              >
                {step}
              </Button>
            </li>
          );
        })}
      </ol>
      <StepStripLegend />
    </div>
  );
}

type StepStripPreviewProps = {
  stepCount: number;
  diagnosis: StripDiagnosis | undefined;
};

export function StepStripPreview({ stepCount, diagnosis }: StepStripPreviewProps) {
  return (
    <ol className="flex flex-wrap justify-center gap-2" aria-label="Steps of the example run">
      {stepNumbers(stepCount).map((step) => {
        const state = stepState(step, diagnosis);
        return (
          <li
            key={step}
            aria-label={`Step ${step}, ${STATE_LABELS[state]}`}
            className={cn(
              TILE_CLASSES,
              "flex items-center justify-center transition-colors duration-500 motion-reduce:transition-none",
              STATE_CLASSES[state]
            )}
          >
            {step}
          </li>
        );
      })}
    </ol>
  );
}
