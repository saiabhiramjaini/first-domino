import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { FailuresInbox } from "@/features/failures";

export const metadata: Metadata = { title: "Failures" };

export default function FailuresPage() {
  return (
    <>
      <PageHeader
        title="Failures"
        description="Failed agent runs and the first step that doomed each one."
      />
      <FailuresInbox />
    </>
  );
}
