"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createApiKey, type CreateApiKeyRequest } from "@/api/generated";
import { zCreateApiKeyResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";
import { listApiKeysKey } from "./use-list-api-keys";

export function useCreateApiKey() {
  const { auth } = useApiAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateApiKeyRequest) =>
      callApi(createApiKey({ auth, body }), zCreateApiKeyResponse),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: listApiKeysKey() }),
  });
}
