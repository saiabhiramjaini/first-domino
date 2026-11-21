"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { revokeApiKey } from "@/api/generated";
import { zRevokeApiKeyResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";
import { listApiKeysKey } from "./use-list-api-keys";

export function useRevokeApiKey() {
  const { auth } = useApiAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (apiKeyId: string) =>
      callApi(revokeApiKey({ auth, body: { api_key_id: apiKeyId } }), zRevokeApiKeyResponse),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: listApiKeysKey() }),
  });
}
