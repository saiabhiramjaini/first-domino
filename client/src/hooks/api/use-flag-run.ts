"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { flagRun, type FlagRunRequest } from "@/api/generated";
import { zFlagRunResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";
import { getRunKey } from "./use-get-run";

export function useFlagRun() {
  const { auth } = useApiAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: FlagRunRequest) => callApi(flagRun({ auth, body }), zFlagRunResponse),
    onSuccess: async (data) => {
      queryClient.setQueryData(getRunKey(data.run.id), data);
      // Flagging also starts a diagnosis, so the run is re-read for its latest diagnosis id.
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: getRunKey(data.run.id) }),
        queryClient.invalidateQueries({ queryKey: ["runs", "list"] }),
        queryClient.invalidateQueries({ queryKey: ["runs", "count"] }),
        queryClient.invalidateQueries({ queryKey: ["diagnoses", "list"] }),
        queryClient.invalidateQueries({ queryKey: ["diagnoses", "count"] }),
      ]);
    },
  });
}
