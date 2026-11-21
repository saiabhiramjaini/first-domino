"use client";

import { Button } from "@/components/ui/button";

type GlobalErrorProps = { reset: () => void };

export default function GlobalError({ reset }: GlobalErrorProps) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col items-center justify-center gap-4">
        <h2 className="text-lg font-semibold">Something went wrong</h2>
        <Button onClick={reset}>Try again</Button>
      </body>
    </html>
  );
}
