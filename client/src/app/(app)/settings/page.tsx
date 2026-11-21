import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { SettingsPage } from "@/features/settings";

export const metadata: Metadata = { title: "Settings" };

export default function Page() {
  return (
    <>
      <PageHeader
        title="Connect your agent"
        description="Four steps. Each one ticks itself as soon as First Domino sees it working."
      />
      <SettingsPage />
    </>
  );
}
