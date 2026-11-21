import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { RunsList } from "@/features/runs";

export const metadata: Metadata = { title: "Runs" };

export default function RunsPage() {
  return (
    <>
      <PageHeader
        title="Runs"
        description="Every run your agent records, with its full trace, updated live while it runs."
      />
      <RunsList />
    </>
  );
}
