import { Badge } from "@/components/ui/badge";

import { TONE_BADGE_VARIANT, type ToneLabel } from "./tone";

type StatusBadgeProps = { status: ToneLabel; className?: string; dot?: boolean };

export function StatusBadge({ status, className, dot = true }: StatusBadgeProps) {
  return (
    <Badge variant={TONE_BADGE_VARIANT[status.tone]} className={className}>
      {dot && <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />}
      {status.label}
    </Badge>
  );
}
