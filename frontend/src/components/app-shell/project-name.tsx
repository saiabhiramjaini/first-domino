"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { useGetProjectSelf } from "@/hooks/api/use-get-project-self";

export function ProjectName() {
  const project = useGetProjectSelf();
  return (
    <div className="flex flex-col gap-0.5 rounded-lg border bg-background px-2.5 py-2">
      <span className="text-xs text-muted-foreground">Project</span>
      {project.data ? (
        <span className="truncate text-sm font-medium">{project.data.name}</span>
      ) : project.isError ? (
        <span className="text-sm text-muted-foreground">Unavailable</span>
      ) : (
        <Skeleton className="h-5 w-28" />
      )}
    </div>
  );
}
