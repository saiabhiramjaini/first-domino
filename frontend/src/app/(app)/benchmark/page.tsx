import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";

export const metadata: Metadata = { title: "Benchmark" };

export default function Page() {
  return (
    <PageHeader title="Benchmark" description="How First Domino compares with reading the trace." />
  );
}
