import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { z } from "zod";

import { CauseDetail } from "@/features/causes";

export const metadata: Metadata = { title: "Root cause" };

const CauseIdSchema = z.uuid();

export default async function CausePage({ params }: PageProps<"/causes/[causeId]">) {
  const { causeId } = await params;
  const parsed = CauseIdSchema.safeParse(causeId);
  if (!parsed.success) notFound();
  return <CauseDetail causeId={parsed.data} />;
}
