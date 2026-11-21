import type { ApiErrorCode } from "@/api/generated";
import { zApiError } from "@/api/generated/zod.gen";

export type ClientErrorCode = "network_error" | "unexpected_response";

export type ApiErrorFields = {
  status: number;
  code: ApiErrorCode | ClientErrorCode;
  title: string;
  detail: string;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode | ClientErrorCode;
  readonly title: string;
  readonly detail: string;

  constructor(fields: ApiErrorFields) {
    super(`${fields.status} ${fields.code}: ${fields.title}`);
    this.name = "ApiError";
    this.status = fields.status;
    this.code = fields.code;
    this.title = fields.title;
    this.detail = fields.detail;
  }
}

export function apiErrorFromResponse(status: number, body: unknown): ApiError {
  const parsed = zApiError.safeParse(body);
  if (parsed.success) return new ApiError({ status, ...parsed.data });
  return new ApiError({
    status,
    code: "unexpected_response",
    title: "The API answered with an unexpected error",
    detail: `Status ${status} without a standard error body.`,
  });
}

export function networkError(): ApiError {
  return new ApiError({
    status: 0,
    code: "network_error",
    title: "Could not reach the API",
    detail: "Check your connection and that the API is running.",
  });
}

export function invalidResponseError(status: number): ApiError {
  return new ApiError({
    status,
    code: "unexpected_response",
    title: "The API answered in an unexpected shape",
    detail: "The web app and the API may be on different contract versions.",
  });
}

export function isApiError(error: unknown, code?: ApiErrorFields["code"]): error is ApiError {
  return error instanceof ApiError && (code === undefined || error.code === code);
}
