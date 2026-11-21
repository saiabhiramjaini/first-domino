import { FailedRunsTable } from "./failed-runs-table";
import { InboxStats } from "./inbox-stats";
import { TopCauses } from "./top-causes";

export function FailuresInbox() {
  return (
    <div className="flex flex-col gap-6">
      <InboxStats />
      <div className="grid gap-6 lg:grid-cols-3">
        <section className="flex min-w-0 flex-col gap-3 lg:col-span-2" aria-labelledby="runs-title">
          <h2 id="runs-title" className="font-medium">
            Failed runs
          </h2>
          <FailedRunsTable />
        </section>
        <section className="flex flex-col gap-3" aria-labelledby="causes-title">
          <h2 id="causes-title" className="font-medium">
            Top root causes
          </h2>
          <TopCauses />
        </section>
      </div>
    </div>
  );
}
