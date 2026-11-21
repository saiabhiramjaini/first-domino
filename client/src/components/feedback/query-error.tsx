"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { reportClientError } from "@/lib/report-client-error";

import { errorCopy } from "./error-copy";

type QueryErrorProps = {
  error: unknown;
  what: string;
  source: string;
  onRetry: () => void;
};

export function QueryError({ error, what, source, onRetry }: QueryErrorProps) {
  useEffect(() => {
    reportClientError(error, source);
  }, [error, source]);

  const copy = errorCopy(error, what);
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-2 rounded-lg border border-destructive/30 p-4"
    >
      <p className="text-sm font-medium text-destructive">{copy.title}</p>
      <p className="text-sm text-muted-foreground">{copy.description}</p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}
