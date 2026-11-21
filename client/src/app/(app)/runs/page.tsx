import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { InboxStats } from "@/features/failures";
import { RunsList, runFilterFrom } from "@/features/runs";

export const metadata: Metadata = { title: "Runs" };

export default async function RunsPage({ searchParams }: PageProps<"/runs">) {
  const filter = runFilterFrom((await searchParams).status);
  return (
    <>
      <PageHeader
        title="Runs"
        description="Every run your agent records, live. Failed runs are diagnosed on their own."
      />
      <InboxStats />
      {/* Keyed so a link to /runs (sidebar, logo) resets the tab, not only the URL. */}
      <RunsList key={filter} initialFilter={filter} />
    </>
  );
}
