"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { useGetProjectSelf } from "@/hooks/api/use-get-project-self";

function initial(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "P";
}

export function ProjectName() {
  const project = useGetProjectSelf();
  return (
    <div className="flex h-8 items-center gap-2 px-2" title={project.data?.name}>
      <span
        className="flex size-5 shrink-0 items-center justify-center rounded bg-muted text-[11px] font-semibold text-muted-foreground"
        aria-hidden="true"
      >
        {project.data ? initial(project.data.name) : "·"}
      </span>
      {project.data ? (
        <span className="truncate text-sm font-medium">{project.data.name}</span>
      ) : project.isError ? (
        <span className="text-sm text-muted-foreground">Unavailable</span>
      ) : (
        <Skeleton className="h-4 w-28" />
      )}
    </div>
  );
}
