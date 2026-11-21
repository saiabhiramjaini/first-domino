import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";

export const metadata: Metadata = { title: "Settings" };

export default function Page() {
  return (
    <PageHeader title="Settings" description="Connect your agent and choose where alerts go." />
  );
}
