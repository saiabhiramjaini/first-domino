"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { useGetProjectSelf } from "@/hooks/api/use-get-project-self";
import { formatDateTime } from "@/lib/format";

import { CopyButton } from "./copy-button";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-11 flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-2">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="flex min-w-0 items-center gap-1 text-sm">{children}</dd>
    </div>
  );
}

export function ProjectDetails() {
  const project = useGetProjectSelf();
  const data = project.data;
  return (
    <dl className="flex flex-col divide-y rounded-md border">
      <Row label="Name">{data ? data.name : <Skeleton className="h-4 w-32" />}</Row>
      <Row label="Project ID">
        {data ? (
          <>
            <span className="truncate font-mono text-xs">{data.id}</span>
            <CopyButton value={data.id} label="Copy the project ID" />
          </>
        ) : (
          <Skeleton className="h-4 w-64" />
        )}
      </Row>
      <Row label="API URL">
        <span className="truncate font-mono text-xs">{API_URL}</span>
        <CopyButton value={API_URL} label="Copy the API URL" />
      </Row>
      <Row label="Created">
        {data ? formatDateTime(data.created_at) : <Skeleton className="h-4 w-36" />}
      </Row>
    </dl>
  );
}
