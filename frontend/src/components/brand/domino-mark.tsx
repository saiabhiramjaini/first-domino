import { cn } from "@/lib/utils";

type DominoMarkProps = { className?: string };

export function DominoMark({ className }: DominoMarkProps) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={cn("size-6", className)}>
      <rect x="4" y="8" width="7" height="18" rx="1.5" className="fill-domino" />
      <rect
        x="14"
        y="8"
        width="7"
        height="18"
        rx="1.5"
        transform="rotate(18 17.5 26)"
        className="fill-foreground/70"
      />
      <rect
        x="23"
        y="10"
        width="7"
        height="18"
        rx="1.5"
        transform="rotate(38 26.5 28)"
        className="fill-foreground/40"
      />
    </svg>
  );
}
