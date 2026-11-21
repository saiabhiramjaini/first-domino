"use client";

import { useMutation } from "@tanstack/react-query";

import { exportCause } from "@/api/generated";
import { zExportCauseResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";

export function useExportCause() {
  const { auth } = useApiAuth();
  return useMutation({
    mutationFn: (causeId: string) =>
      callApi(exportCause({ auth, body: { cause_id: causeId } }), zExportCauseResponse),
  });
}
