import { DominoMark } from "./domino-mark";

export function BrandName() {
  return (
    <span className="flex items-center gap-2 font-semibold tracking-tight">
      <DominoMark />
      First Domino
    </span>
  );
}
