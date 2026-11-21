"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useGetProjectSelf } from "@/hooks/api/use-get-project-self";

export function ProjectName() {
  const project = useGetProjectSelf();
  return (
    <div className="flex flex-col gap-0.5 rounded-lg border bg-background px-2.5 py-2">
      <span className="text-xs text-muted-foreground">Project</span>
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
        <Skeleton className="h-5 w-28" />
      )}
    </div>
  );
}
