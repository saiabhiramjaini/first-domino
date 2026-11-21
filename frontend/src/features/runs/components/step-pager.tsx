"use client";

import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

type StepPagerProps = {
  selectedStep: number;
  stepCount: number;
  onSelectStep: (step: number) => void;
};

export function StepPager({ selectedStep, stepCount, onSelectStep }: StepPagerProps) {
  return (
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Show the previous step"
        disabled={selectedStep <= 1}
        onClick={() => onSelectStep(selectedStep - 1)}
      >
        <ChevronLeftIcon />
      </Button>
      <span className="text-xs text-muted-foreground tabular-nums">
        {selectedStep} of {stepCount}
      </span>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Show the next step"
        disabled={selectedStep >= stepCount}
        onClick={() => onSelectStep(selectedStep + 1)}
      >
        <ChevronRightIcon />
      </Button>
    </div>
  );
}
