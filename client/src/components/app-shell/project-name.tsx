"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useGetProjectSelf } from "@/hooks/api/use-get-project-self";

function initial(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "P";
}

export function ProjectName() {
  const project = useGetProjectSelf();
  return (
    <div className="flex items-center gap-2.5 rounded-lg border bg-background/60 px-2.5 py-2">
      <span
        className="flex size-7 shrink-0 items-center justify-center rounded-md bg-domino/15 text-xs font-semibold text-domino"
        aria-hidden="true"
      >
        {project.data ? initial(project.data.name) : "·"}
      </span>
      <div className="flex min-w-0 flex-col">
        <span className="text-[11px] text-muted-foreground">Project</span>
        {project.data ? (
          <Tooltip>
            <TooltipTrigger
              render={<span tabIndex={0} />}
              className="truncate rounded-sm text-sm font-medium outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              {project.data.name}
            </TooltipTrigger>
            <TooltipContent side="right">{project.data.name}</TooltipContent>
          </Tooltip>
        ) : project.isError ? (
          <span className="text-sm text-muted-foreground">Unavailable</span>
        ) : (
          <Skeleton className="mt-0.5 h-4 w-24" />
        )}
      </div>
    </div>
  );
}
