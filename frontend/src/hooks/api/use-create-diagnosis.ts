"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createDiagnosis } from "@/api/generated";
import { zCreateDiagnosisResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";
import { getDiagnosisKey } from "./use-get-diagnosis";
import { getRunKey } from "./use-get-run";

export function useCreateDiagnosis() {
  const { auth } = useApiAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) =>
      callApi(createDiagnosis({ auth, body: { run_id: runId } }), zCreateDiagnosisResponse),
    onSuccess: async (data) => {
      queryClient.setQueryData(getDiagnosisKey(data.diagnosis.id), data);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: getRunKey(data.diagnosis.run_id) }),
        queryClient.invalidateQueries({ queryKey: ["diagnoses", "list"] }),
        queryClient.invalidateQueries({ queryKey: ["diagnoses", "count"] }),
      ]);
    },
  });
}
