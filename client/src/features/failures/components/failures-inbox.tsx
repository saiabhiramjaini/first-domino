import Link from "next/link";

import { Panel } from "@/components/layout/panel";
import { buttonVariants } from "@/components/ui/button";

import { FailedRunsTable } from "./failed-runs-table";
import { InboxStats } from "./inbox-stats";
import { TopCauses } from "./top-causes";

export function FailuresInbox() {
  return (
    <div className="flex flex-col gap-6">
      <InboxStats />
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <Panel
          id="failed-runs"
          title="Failed runs"
          description="Newest first. Open a run to see its first domino and the replays that prove it."
        >
          <FailedRunsTable />
        </Panel>
        <Panel
          id="top-causes"
          title="Top root causes"
          description="Failures grouped by what went wrong."
          actions={
            <Link href="/causes" className={buttonVariants({ variant: "ghost", size: "sm" })}>
              View all
            </Link>
          }
        >
          <TopCauses />
        </Panel>
      </div>
    </div>
  );
}
