import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { CausesList } from "@/features/causes";

export const metadata: Metadata = { title: "Root causes" };

export default function CausesPage() {
  return (
    <>
      <PageHeader
        title="Root causes"
        description="Failures grouped by the step that doomed them, most runs first."
      />
      <CausesList />
    </>
  );
}
