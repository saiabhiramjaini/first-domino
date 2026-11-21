"use client";

import { toast } from "sonner";

import type { Diagnosis } from "@/api/generated";
import { Button } from "@/components/ui/button";
import { useCreateDiagnosis } from "@/hooks/api/use-create-diagnosis";
import { isApiError } from "@/lib/api-error";
import { reportClientError } from "@/lib/report-client-error";

type DiagnoseRunButtonProps = {
  runId: string;
  hasDiagnosis: boolean;
  onCreated: (diagnosis: Diagnosis) => void;
};

export function DiagnoseRunButton({ runId, hasDiagnosis, onCreated }: DiagnoseRunButtonProps) {
  const createDiagnosis = useCreateDiagnosis();

  async function handleClick() {
    try {
      const { diagnosis } = await createDiagnosis.mutateAsync(runId);
      onCreated(diagnosis);
      toast.success("Diagnosis started. Replays will show up below as they finish.");
    } catch (error) {
      if (isApiError(error, "conflict")) {
        toast.error("A diagnosis is already running for this run. Wait for it to finish.");
        return;
      }
      reportClientError(error, "runs.diagnose");
      toast.error("Could not start the diagnosis. Check that the API is running and try again.");
    }
  }

  return (
    <Button onClick={handleClick} disabled={createDiagnosis.isPending}>
      {createDiagnosis.isPending ? "Starting..." : hasDiagnosis ? "Diagnose again" : "Diagnose run"}
    </Button>
  );
}
