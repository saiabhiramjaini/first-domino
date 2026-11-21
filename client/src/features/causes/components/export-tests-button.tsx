"use client";

import { DownloadIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useExportCause } from "@/hooks/api/use-export-cause";
import { formatCount } from "@/lib/format";
import { reportClientError } from "@/lib/report-client-error";

import { exportFileBody, exportFileName } from "../export-file";

const TEST_CASE_NOUN = { one: "test case", other: "test cases" };

function download(fileName: string, body: string) {
  const url = URL.createObjectURL(new Blob([body], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

type ExportTestsButtonProps = { causeId: string };

export function ExportTestsButton({ causeId }: ExportTestsButtonProps) {
  const exportCause = useExportCause();

  async function handleClick() {
    try {
      const { export: causeExport } = await exportCause.mutateAsync(causeId);
      download(exportFileName(causeExport), exportFileBody(causeExport));
      toast.success(
        `Exported ${formatCount(causeExport.cases.length, TEST_CASE_NOUN)}. Add them to your eval suite.`
      );
    } catch (error) {
      reportClientError(error, "causes.export_tests");
      toast.error("Could not export the tests. Check that the API is running and try again.");
    }
  }

  return (
    <Button variant="outline" onClick={handleClick} disabled={exportCause.isPending}>
      <DownloadIcon data-icon="inline-start" aria-hidden="true" />
      {exportCause.isPending ? "Exporting..." : "Export as tests"}
    </Button>
  );
}
