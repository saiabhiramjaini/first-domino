import { cn } from "@/lib/utils";

const STEPS = 9;
const DOMINO = 6;

// A static picture of the run page: the answer, the proof and the step strip.
export function ProductPreview() {
  return (
    <div className="relative w-full">
      <div
        className="glow-domino pointer-events-none absolute -inset-x-20 -top-24 h-72"
        aria-hidden="true"
      />
      <figure
        aria-label="Example diagnosis: step 6 is the first domino, proven by 5 of 5 replays"
        className="relative overflow-hidden rounded-2xl border bg-card shadow-2xl shadow-black/40"
      >
        <div className="flex items-center gap-2 border-b px-4 py-3" aria-hidden="true">
          <span className="size-2.5 rounded-full bg-muted-foreground/30" />
          <span className="size-2.5 rounded-full bg-muted-foreground/30" />
          <span className="size-2.5 rounded-full bg-muted-foreground/30" />
          <span className="ml-3 font-mono text-xs text-muted-foreground">
            failures / run 7f3a91c2
          </span>
        </div>
        <div className="flex flex-col gap-6 p-5 sm:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex flex-col gap-2 text-left">
              <span className="inline-flex w-fit items-center gap-1.5 rounded-md border border-verified/25 bg-verified/10 px-1.5 py-0.5 text-xs font-medium text-verified">
                <span className="size-1.5 rounded-full bg-current" />
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
            <dl className="grid grid-cols-4 gap-5 rounded-lg border bg-background/50 px-4 py-3 text-left">
              {[
                ["First domino", "#6", "text-domino"],
                ["Proof", "5/5", "text-verified"],
                ["Replays", "17", ""],
                ["Cost", "$0.014", ""],
              ].map(([label, value, tone]) => (
                <div key={label} className="flex flex-col gap-1">
                  <dt className="text-[11px] text-muted-foreground">{label}</dt>
                  <dd className={cn("font-mono text-base font-medium", tone)}>{value}</dd>
                </div>
              ))}
            </dl>
          </div>
          <ol className="flex flex-wrap items-end gap-2 border-t pt-5" aria-hidden="true">
            {Array.from({ length: STEPS }, (_, offset) => offset + 1).map((step) => (
              <li
                key={step}
                className={cn(
                  "flex h-12 w-9 items-center justify-center rounded-md border font-mono text-xs",
                  step < DOMINO && "border-transparent bg-ruled-out/60 text-muted-foreground/70",
                  step === DOMINO &&
                    "-rotate-6 border-domino bg-domino text-domino-foreground shadow-[0_0_24px_-4px_var(--domino)] ring-2 ring-verified ring-offset-2 ring-offset-card",
                  step > DOMINO && "border-border bg-muted/40 text-muted-foreground"
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
