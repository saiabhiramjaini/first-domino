"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { stepState, type StepState, type StripDiagnosis } from "../step-strip-state";

const STATE_CLASSES = {
  idle: "border-border bg-card text-muted-foreground",
  in_range: "border-search-range bg-search-range/15 text-search-range",
  ruled_out: "border-transparent bg-ruled-out text-ruled-out-foreground",
  first_domino: "border-domino bg-domino text-domino-foreground shadow-sm",
  verified_domino:
    "border-domino bg-domino text-domino-foreground shadow-sm ring-2 ring-verified ring-offset-2 ring-offset-background",
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
  const steps = Array.from({ length: stepCount }, (_, offset) => offset + 1);
  return (
    <div className="flex flex-col gap-3">
      <ol className="flex flex-wrap gap-1.5" aria-label="Steps of this run">
        {steps.map((step) => {
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
                  "size-10 tabular-nums",
                  STATE_CLASSES[state],
                  isSelected && "outline-2 outline-offset-2 outline-foreground"
                )}
              >
                {step}
              </Button>
            </li>
          );
        })}
      </ol>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {LEGEND.map((item) => (
          <li key={item.state} className="flex items-center gap-1.5">
            <span className={cn("size-3 rounded-sm border", STATE_CLASSES[item.state])} />
            {item.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
