import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type Metric = {
  label: string;
  value: string | undefined;
  hint?: string;
  tone?: "default" | "domino" | "verified";
};

const TONE_CLASS = {
  default: "text-foreground",
  domino: "text-domino",
  verified: "text-verified",
} as const;

// Key numbers in one bordered strip, split by dividers.
export function MetricStrip({ metrics }: { metrics: readonly Metric[] }) {
  return (
    <dl className="grid grid-cols-2 overflow-hidden rounded-xl border bg-card lg:grid-flow-col lg:grid-cols-none">
      {metrics.map((metric, index) => (
        <div
          key={metric.label}
          className={cn(
            "flex flex-col gap-2 border-border p-4",
            index % 2 === 1 && "border-l",
            index >= 2 && "border-t lg:border-t-0",
            index >= 1 && "lg:border-l"
          )}
        >
          <dt className="text-xs font-medium text-muted-foreground">{metric.label}</dt>
          <dd className="flex flex-col gap-1">
            {metric.value === undefined ? (
              <Skeleton className="h-8 w-14" />
            ) : (
              <span
                className={cn(
                  "font-mono text-3xl font-medium tracking-tight tabular-nums",
                  TONE_CLASS[metric.tone ?? "default"]
                )}
              >
                {metric.value}
              </span>
            )}
            {metric.hint && <span className="text-xs text-muted-foreground">{metric.hint}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}
