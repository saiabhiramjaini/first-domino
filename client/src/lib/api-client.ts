import type { z } from "zod";

import { client } from "@/api/generated/client.gen";

import { apiErrorFromResponse, invalidResponseError, networkError } from "./api-error";

const DEFAULT_API_URL = "http://localhost:8000";

client.setConfig({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL });

type ApiCallResult = { data?: unknown; error?: unknown; response?: Response };

export async function callApi<T>(call: Promise<ApiCallResult>, schema: z.ZodType<T>): Promise<T> {
  const { data, error, response } = await call;
  if (!response) throw networkError();
  if (error !== undefined || !response.ok) throw apiErrorFromResponse(response.status, error);
  const parsed = schema.safeParse(data);
  if (!parsed.success) throw invalidResponseError(response.status);
  return parsed.data;
}
