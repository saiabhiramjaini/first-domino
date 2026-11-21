import { cn } from "@/lib/utils";

type DominoMarkProps = { className?: string };

// The logo (public/brand/logo.svg): the first domino, fallen, beside the dashed outline of where
// it stood, which is what the proven fix keeps standing. The favicon (src/app/icon.svg) draws the
// outline solid, since dashes blur at 16 px.
export function DominoMark({ className }: DominoMarkProps) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={cn("size-7 shrink-0", className)}>
      <rect
        x="17.3"
        y="7.3"
        width="7.4"
        height="18.4"
        rx="2"
        fill="none"
        stroke="#8B7CFF"
        strokeWidth="1.6"
        strokeDasharray="2.2 1.8"
        opacity=".75"
      />
      <rect
        x="16.5"
        y="6.5"
        width="9"
        height="20"
        rx="2.6"
        fill="#8B7CFF"
        transform="rotate(-34 16.5 26.5)"
      />
    </svg>
  );
}
