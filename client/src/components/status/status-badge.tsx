import { Badge } from "@/components/ui/badge";

import { TONE_BADGE_VARIANT, type ToneLabel } from "./tone";

type StatusBadgeProps = { status: ToneLabel; className?: string };

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Badge variant={TONE_BADGE_VARIANT[status.tone]} className={className}>
      {status.label}
    </Badge>
  );
}
