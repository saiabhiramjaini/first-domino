import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type Metric = {
  label: string;
  value: string | undefined;
  hint?: string;
  tone?: "default" | "domino" | "verified";
};

// Key numbers in one bordered strip, split by dividers.
export function MetricStrip({ metrics }: { metrics: readonly Metric[] }) {
  return (
    <dl className="grid grid-cols-2 overflow-hidden rounded-lg border lg:grid-flow-col lg:grid-cols-none">
      {metrics.map((metric, index) => (
        <div
          key={metric.label}
          className={cn(
            "flex flex-col gap-1 border-border px-4 py-3",
            index % 2 === 1 && "border-l",
            index >= 2 && "border-t lg:border-t-0",
            index >= 1 && "lg:border-l"
          )}
        >
          <dt className="text-xs text-muted-foreground">{metric.label}</dt>
          <dd className="flex flex-col gap-1">
            {metric.value === undefined ? (
              <Skeleton className="h-7 w-14" />
            ) : (
              <span className="text-2xl font-semibold tracking-tight tabular-nums">
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
