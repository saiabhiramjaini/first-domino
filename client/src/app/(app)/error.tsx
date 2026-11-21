"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { reportClientError } from "@/lib/report-client-error";

type SignedInErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function SignedInError({ error, reset }: SignedInErrorProps) {
  useEffect(() => {
    reportClientError(error, "app.signed_in_error_boundary");
  }, [error]);

  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-lg border border-destructive/30 p-6"
    >
      <h2 className="font-semibold">This page could not be shown</h2>
      <p className="text-sm text-muted-foreground">
        Try again. If it keeps failing, reload the page or open another section from the menu.
      </p>
      {error.digest && <p className="text-xs text-muted-foreground">Reference: {error.digest}</p>}
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
