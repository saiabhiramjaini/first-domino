"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { setProjectSlackWebhook, type SetProjectSlackWebhookRequest } from "@/api/generated";
import { zSetProjectSlackWebhookResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";
import { getProjectSelfKey } from "./use-get-project-self";

export function useSetProjectSlackWebhook() {
  const { auth } = useApiAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: SetProjectSlackWebhookRequest) =>
      callApi(setProjectSlackWebhook({ auth, body }), zSetProjectSlackWebhookResponse),
    onSuccess: (data) => {
      queryClient.setQueryData(getProjectSelfKey(), { project: data.project });
    },
  });
}
