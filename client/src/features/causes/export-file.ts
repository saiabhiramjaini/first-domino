import type { CauseExport } from "@/api/generated";

export function exportFileName(causeExport: Pick<CauseExport, "cause_id" | "exported_at">): string {
  const date = causeExport.exported_at.slice(0, 10);
  return `first-domino-regression-tests-${causeExport.cause_id.slice(0, 8)}-${date}.json`;
}

export function exportFileBody(causeExport: CauseExport): string {
  return `${JSON.stringify(causeExport, null, 2)}\n`;
}
