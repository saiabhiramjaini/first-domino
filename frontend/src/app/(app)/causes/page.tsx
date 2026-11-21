import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";

export const metadata: Metadata = { title: "Root causes" };

export default function Page() {
  return (
    <PageHeader title="Root causes" description="Failures grouped by the step that doomed them." />
  );
}
