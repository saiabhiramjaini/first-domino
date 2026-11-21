"use client";

import { ArrowUpRightIcon } from "lucide-react";

import { QueryError } from "@/components/feedback/query-error";
import { Skeleton } from "@/components/ui/skeleton";
import { useGetProjectSelf } from "@/hooks/api/use-get-project-self";
import { formatDateTime } from "@/lib/format";

import { CopyButton } from "./copy-button";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const SDK_URL =
  "https://github.com/saiabhiramjaini/first-domino/tree/main/server/packages/first-domino";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 px-4 py-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="flex min-h-6 min-w-0 items-center justify-between gap-2 text-sm">
        {children}
      </dd>
    </div>
  );
}

// The project's details, kept in a narrow column beside the setup steps.
export function ProjectDetails() {
  const project = useGetProjectSelf();
  const data = project.data;
  return (
    <div className="flex flex-col gap-3">
      {project.isLoadingError && (
        <QueryError
          error={project.error}
          what="the project"
          source="settings.load_project"
          onRetry={() => void project.refetch()}
        />
      )}
      <dl className="flex flex-col divide-y overflow-hidden rounded-lg border">
        <Row label="Name">
          {data ? <span className="truncate">{data.name}</span> : <Skeleton className="h-4 w-32" />}
        </Row>
        <Row label="Project ID">
          {data ? (
            <>
              <span className="truncate font-mono text-xs">{data.id}</span>
              <CopyButton value={data.id} label="Copy the project ID" />
            </>
          ) : (
            <Skeleton className="h-4 w-48" />
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
      <a
        href={SDK_URL}
        target="_blank"
        rel="noreferrer"
        className="flex items-center justify-between gap-3 rounded-lg border px-4 py-3 text-sm outline-none hover:bg-muted/40 focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <span className="flex flex-col gap-0.5">
          <span className="font-medium">SDK on GitHub</span>
          <span className="text-xs text-muted-foreground">Source code and README</span>
        </span>
        <ArrowUpRightIcon className="size-4 text-muted-foreground" aria-hidden="true" />
      </a>
    </div>
  );
}
