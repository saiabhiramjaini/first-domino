"use client";

import { useNow } from "@/hooks/use-now";
import { formatRelative } from "@/lib/format";

import type { FailureReason } from "../run-flag";

const CLOCK_MS = 60_000;

type FailureReasonTextProps = { failure: FailureReason };

// Inline content for the run header's description line.
export function FailureReasonText({ failure }: FailureReasonTextProps) {
  const now = useNow(failure.flaggedAt === null ? false : CLOCK_MS);
  return (
    <span className="line-clamp-3 whitespace-pre-line" title={failure.reason}>
      <span className="font-medium text-foreground">{failure.label}:</span> {failure.reason}
      {failure.flaggedAt !== null && <span> · {formatRelative(failure.flaggedAt, now)}</span>}
    </span>
  );
}
