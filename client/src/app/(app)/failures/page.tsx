import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { FailuresInbox } from "@/features/failures";

export const metadata: Metadata = { title: "Failures" };

export default function FailuresPage() {
  return (
    <>
      <PageHeader
        title="Failures"
        description="Every failed run, the first step that doomed it, and whether a fix proved it."
      />
      <FailuresInbox />
    </>
  );
}
