import { cn } from "@/lib/utils";

const STEP_COUNT = 9;
const FIRST_DOMINO = 4;

type DominoTileState = "standing" | "first" | "fallen";

const TILE_CLASSES = {
  standing: "bg-card border-border text-muted-foreground",
  first: "bg-domino border-domino text-domino-foreground -rotate-6 shadow-md",
  fallen: "bg-muted border-border text-muted-foreground rotate-12 opacity-70",
} as const satisfies Record<DominoTileState, string>;

function tileState(step: number): DominoTileState {
  if (step < FIRST_DOMINO) return "standing";
  if (step === FIRST_DOMINO) return "first";
  return "fallen";
}

export function DominoRow() {
  const steps = Array.from({ length: STEP_COUNT }, (_, offset) => offset + 1);
  return (
    <figure className="flex flex-col items-center gap-4">
      <ol className="flex items-end gap-1.5 sm:gap-2.5" aria-label="Agent run steps">
        {steps.map((step) => {
          const state = tileState(step);
          return (
            <li
              key={step}
              aria-current={state === "first" ? "step" : undefined}
              className={cn(
                "flex h-16 w-7 origin-bottom items-start justify-center rounded-md border pt-1.5 text-xs font-medium transition-transform sm:h-20 sm:w-9",
                TILE_CLASSES[state]
              )}
            >
              {step}
            </li>
          );
        })}
      </ol>
      <figcaption className="max-w-sm text-center text-sm text-muted-foreground">
        Step 4 is the first domino: replays from step 3 can still succeed, replays from step 4
        always fail.
      </figcaption>
    </figure>
  );
}
