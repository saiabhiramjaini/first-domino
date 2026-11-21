import { cn } from "@/lib/utils";

import type { Tone, ToneLabel } from "./tone";

type StatusBadgeProps = { status: ToneLabel; className?: string; dot?: boolean };

// The dot carries the only color: red for a failure, violet for the first domino, gray for the
// rest. A running state pulses.
const DOT_CLASS = {
  neutral: "bg-muted-foreground/60",
  info: "bg-foreground",
  success: "bg-foreground/80",
  warning: "bg-muted-foreground",
  danger: "bg-destructive",
  domino: "bg-domino",
} as const satisfies Record<Tone, string>;

const TEXT_CLASS = {
  neutral: "text-muted-foreground",
  info: "text-foreground",
  success: "text-foreground",
  warning: "text-muted-foreground",
  danger: "text-foreground",
  domino: "text-domino",
} as const satisfies Record<Tone, string>;

export function StatusBadge({ status, className, dot = true }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex w-fit shrink-0 items-center gap-1.5 text-xs font-medium whitespace-nowrap",
        TEXT_CLASS[status.tone],
        className
      )}
    >
      {dot && (
        <span className="relative flex size-1.5" aria-hidden="true">
          {status.tone === "info" && (
            <span
              className={cn(
                "absolute inline-flex size-full animate-ping rounded-full opacity-60 motion-reduce:animate-none",
                DOT_CLASS.info
              )}
            />
          )}
          <span
            className={cn("relative inline-flex size-1.5 rounded-full", DOT_CLASS[status.tone])}
          />
        </span>
      )}
      {status.label}
    </span>
  );
}
