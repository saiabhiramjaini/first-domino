"use client";

import { QueryError } from "@/components/feedback/query-error";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useGetProjectSelf } from "@/hooks/api/use-get-project-self";
import { formatDateTime } from "@/lib/format";

export function ProjectCard() {
  const project = useGetProjectSelf();
  return (
    <Card>
      <CardHeader>
        <CardTitle>Project</CardTitle>
        <CardDescription>Created for you on your first sign-in.</CardDescription>
      </CardHeader>
      <CardContent>
        {project.isError ? (
          <QueryError
            error={project.error}
            what="your project"
            source="settings.load_project"
            onRetry={() => void project.refetch()}
          />
        ) : (
          <dl className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <dt className="text-sm text-muted-foreground">Name</dt>
              <dd className="font-medium">
                {project.data ? project.data.name : <Skeleton className="h-5 w-32" />}
              </dd>
            </div>
            <div className="flex flex-col gap-1">
              <dt className="text-sm text-muted-foreground">Created</dt>
              <dd className="font-medium">
                {project.data ? (
                  formatDateTime(project.data.created_at)
                ) : (
                  <Skeleton className="h-5 w-40" />
                )}
              </dd>
            </div>
          </dl>
        )}
      </CardContent>
    </Card>
  );
}
