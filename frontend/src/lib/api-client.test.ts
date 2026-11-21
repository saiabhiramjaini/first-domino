import { afterEach, describe, expect, it, vi } from "vitest";

import { getRun } from "@/api/generated";
import { zGetRunResponse } from "@/api/generated/zod.gen";

import { callApi } from "./api-client";
import { ApiError } from "./api-error";

const RUN_ID = "7b0f7c55-8d0e-4a52-9a43-0c8f3f1f2a10";

function respond(status: number, body: unknown) {
  return vi.fn(async () => Response.json(body, { status }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("callApi", () => {
  it("maps an API error body to an ApiError with its code", async () => {
    vi.stubGlobal(
      "fetch",
      respond(404, { code: "not_found", title: "Run not found", detail: "No such run." })
    );
    const error = await callApi(getRun({ query: { run_id: RUN_ID } }), zGetRunResponse).catch(
      (caught: unknown) => caught
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 404, code: "not_found", title: "Run not found" });
  });

  it("rejects a success body that does not match the schema", async () => {
    vi.stubGlobal("fetch", respond(200, { run: { id: RUN_ID } }));
    await expect(
      callApi(getRun({ query: { run_id: RUN_ID } }), zGetRunResponse)
    ).rejects.toMatchObject({ code: "unexpected_response" });
  });

  it("reports a network failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("fetch failed");
      })
    );
    await expect(
      callApi(getRun({ query: { run_id: RUN_ID } }), zGetRunResponse)
    ).rejects.toMatchObject({ code: "network_error" });
  });
});
