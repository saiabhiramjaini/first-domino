import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { SettingsPage } from "@/features/settings";

export const metadata: Metadata = { title: "Settings" };

export default function Page() {
  return (
    <>
      <PageHeader title="Settings" description="Connect your agent and manage this project." />
      <SettingsPage />
    </>
  );
}
