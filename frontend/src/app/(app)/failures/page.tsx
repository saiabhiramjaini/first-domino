import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";

export const metadata: Metadata = { title: "Failures" };

export default function Page() {
  return (
    <PageHeader title="Failures" description="Failed agent runs and the causes behind them." />
  );
}
