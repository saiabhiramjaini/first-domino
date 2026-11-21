"use client";

import { ChevronLeftIcon, ChevronRightIcon, PauseIcon, PlayIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { StepStripLegend, StepStripPreview } from "@/components/runs/run-step-strip";
import { StatusBadge } from "@/components/status/status-badge";
import { CHECK_RESULT } from "@/components/status/status-tones";
import { Button } from "@/components/ui/button";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";

import { DEMO_FRAMES, DEMO_STEP_COUNT } from "../bisect-demo-frames";

const FRAME_MS = 2_600;
const LAST_FRAME = DEMO_FRAMES.length - 1;

export function BisectDemo() {
  const prefersReducedMotion = usePrefersReducedMotion();
  const [frameIndex, setFrameIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const isPlaying = !isPaused && !prefersReducedMotion;
  const frame = DEMO_FRAMES[frameIndex] ?? DEMO_FRAMES[0];

  useEffect(() => {
    if (!isPlaying) return;
    const timer = window.setInterval(() => {
      setFrameIndex((current) => (current >= LAST_FRAME ? 0 : current + 1));
    }, FRAME_MS);
    return () => window.clearInterval(timer);
  }, [isPlaying]);

  function show(index: number) {
    setIsPaused(true);
    setFrameIndex(Math.min(Math.max(index, 0), LAST_FRAME));
  }

  if (!frame) return null;

  return (
    <figure className="flex w-full flex-col gap-5 rounded-2xl border bg-card p-4 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-muted-foreground tabular-nums">
            Stage {frameIndex + 1} of {DEMO_FRAMES.length}
          </span>
          <span className="font-medium">{frame.title}</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Show the previous stage"
            disabled={frameIndex === 0}
            onClick={() => show(frameIndex - 1)}
          >
            <ChevronLeftIcon />
          </Button>
          {!prefersReducedMotion && (
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={isPaused ? "Play the example" : "Pause the example"}
              onClick={() => setIsPaused((paused) => !paused)}
            >
              {isPaused ? <PlayIcon /> : <PauseIcon />}
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Show the next stage"
            disabled={frameIndex === LAST_FRAME}
            onClick={() => show(frameIndex + 1)}
          >
            <ChevronRightIcon />
          </Button>
        </div>
      </div>

      <StepStripPreview stepCount={DEMO_STEP_COUNT} diagnosis={frame.diagnosis} />

      <div className="flex min-h-20 flex-col gap-2" aria-live={isPlaying ? "off" : "polite"}>
        {frame.check && (
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">{frame.check.label}</span>
            <span className="text-muted-foreground">· {frame.check.passed} replays passed</span>
            <StatusBadge status={CHECK_RESULT[frame.check.result]} />
          </div>
        )}
        <figcaption className="text-sm text-muted-foreground">{frame.caption}</figcaption>
      </div>

      <StepStripLegend />
    </figure>
  );
}
