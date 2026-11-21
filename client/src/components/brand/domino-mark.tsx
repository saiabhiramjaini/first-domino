import { cn } from "@/lib/utils";

type DominoMarkProps = { className?: string };

// The logo, identical to the favicon (src/app/icon.svg and public/brand/logo.svg): a ruled-out
// tile, the first domino with its marker, and a doomed tile, on a dark rounded square.
export function DominoMark({ className }: DominoMarkProps) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={cn("size-7 shrink-0", className)}>
      <rect x=".5" y=".5" width="31" height="31" rx="6.5" fill="#18181B" stroke="#2E2E34" />
      <rect x="5.5" y="6" width="5" height="15" rx="1.2" fill="#EDEDEF" opacity=".35" />
      <rect x="13.5" y="6" width="5" height="15" rx="1.2" fill="#8B7CFF" />
      <rect x="21.5" y="6" width="5" height="15" rx="1.2" fill="#EDEDEF" />
      <path d="M16 22.5l3.5 4.5h-7z" fill="#8B7CFF" />
    </svg>
  );
}
