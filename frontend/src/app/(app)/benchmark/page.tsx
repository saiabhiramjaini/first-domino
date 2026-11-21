import type { Metadata } from "next";

import { PageHeader } from "@/components/app-shell/page-header";
import { BenchmarkOverview } from "@/features/benchmark";

export const metadata: Metadata = { title: "Benchmark" };

export default function BenchmarkPage() {
  return (
    <>
      <PageHeader
        title="Benchmark"
        description="How First Domino compares with an LLM judge reading the trace, on labelled failed runs."
      />
      <BenchmarkOverview />
    </>
  );
}
