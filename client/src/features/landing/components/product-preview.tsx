import { cn } from "@/lib/utils";

const STEPS = 9;
const DOMINO = 6;

// A static picture of the run page: the answer, the proof and the step strip.
export function ProductPreview() {
  return (
    <div className="relative w-full">
      <figure
        aria-label="Example diagnosis: step 6 is the first domino, proven by 5 of 5 replays"
        className="relative overflow-hidden rounded-lg border bg-card"
      >
        <div className="flex items-center gap-2 border-b px-4 py-3" aria-hidden="true">
          <span className="size-2.5 rounded-full bg-muted-foreground/30" />
          <span className="size-2.5 rounded-full bg-muted-foreground/30" />
          <span className="size-2.5 rounded-full bg-muted-foreground/30" />
          <span className="ml-3 font-mono text-xs text-muted-foreground">runs / 7f3a91c2</span>
        </div>
        <div className="flex flex-col gap-6 p-5 sm:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex flex-col gap-2 text-left">
              <span className="inline-flex w-fit items-center gap-1.5 text-xs font-medium text-domino">
                <span className="size-1.5 rounded-full bg-domino" />
                Verified
              </span>
              <p className="text-lg font-semibold tracking-tight sm:text-xl">
                Booked 22:00 instead of confirming 10:00
              </p>
              <p className="max-w-md text-sm text-muted-foreground">
                Replays from step 5 can still succeed. Every replay from step 6 fails. Rewriting
                step 6 made the call pass.
              </p>
            </div>
            <dl className="grid grid-cols-4 gap-5 text-left">
              {[
                ["First domino", "#6", "text-domino"],
                ["Proof", "5/5", ""],
                ["Replays", "17", ""],
                ["Cost", "$0.014", ""],
              ].map(([label, value, tone]) => (
                <div key={label} className="flex flex-col gap-1">
                  <dt className="text-xs text-muted-foreground">{label}</dt>
                  <dd className={cn("text-base font-medium tabular-nums", tone)}>{value}</dd>
                </div>
              ))}
            </dl>
          </div>
          <ol className="flex flex-wrap items-end gap-2 border-t pt-5" aria-hidden="true">
            {Array.from({ length: STEPS }, (_, offset) => offset + 1).map((step) => (
              <li
                key={step}
                className={cn(
                  "flex h-10 w-8 items-center justify-center rounded-md border font-mono text-xs",
                  step < DOMINO && "border-transparent bg-muted text-muted-foreground/60",
                  step === DOMINO && "-rotate-6 border-domino bg-domino text-domino-foreground",
                  step > DOMINO && "border-border text-muted-foreground"
                )}
              >
                {step}
              </li>
            ))}
          </ol>
        </div>
      </figure>
    </div>
  );
}
