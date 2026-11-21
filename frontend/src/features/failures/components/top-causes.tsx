"use client";

import Link from "next/link";

import { QueryError } from "@/components/feedback/query-error";
import { StatusBadge } from "@/components/status/status-badge";
import { CAUSE_CATEGORY } from "@/components/status/status-tones";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useListCauses } from "@/hooks/api/use-list-causes";
import { formatCount } from "@/lib/format";
import { RUN_NOUN } from "@/lib/nouns";
import { pageItems } from "@/lib/paging";

import { ALL_CAUSES, TOP_CAUSE_COUNT } from "../inbox-filters";

export function TopCauses() {
  const causes = useListCauses(ALL_CAUSES);
  if (causes.isError) {
    return (
      <QueryError
        error={causes.error}
        what="root causes"
        source="failures.load_causes"
        onRetry={causes.refetch}
      />
    );
  }
  if (causes.isPending) {
    return (
      <div className="flex flex-col gap-2" aria-busy="true">
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-14 w-full" />
      </div>
    );
  }
  const top = pageItems(causes.data).slice(0, TOP_CAUSE_COUNT);
  if (top.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No root causes yet. Each finished diagnosis groups its cause here.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <ul className="flex flex-col divide-y rounded-xl border">
        {top.map((cause) => (
          <li key={cause.id}>
            <Link
              href={`/causes/${cause.id}`}
              className="flex flex-col gap-1.5 p-3 outline-none hover:bg-muted focus-visible:bg-muted"
            >
              <span className="line-clamp-2 text-sm font-medium">{cause.title}</span>
              <span className="flex items-center gap-2 text-xs text-muted-foreground">
                <StatusBadge status={CAUSE_CATEGORY[cause.category]} />
                {formatCount(cause.run_count, RUN_NOUN)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <Link
        href="/causes"
        className={buttonVariants({ variant: "ghost", className: "self-start" })}
      >
        See all root causes
      </Link>
    </div>
  );
}
