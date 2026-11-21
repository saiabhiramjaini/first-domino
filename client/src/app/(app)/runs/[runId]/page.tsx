import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { z } from "zod";

import { RunDiagnosisView } from "@/features/runs";

export const metadata: Metadata = { title: "Run diagnosis" };

const RunIdSchema = z.uuid();

export default async function RunPage({ params }: PageProps<"/runs/[runId]">) {
  const { runId } = await params;
  const parsed = RunIdSchema.safeParse(runId);
  if (!parsed.success) notFound();
  return <RunDiagnosisView runId={parsed.data} />;
}
