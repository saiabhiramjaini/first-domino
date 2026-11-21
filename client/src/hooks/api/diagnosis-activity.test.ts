import { describe, expect, it } from "vitest";

import { zDiagnosisStatus } from "@/api/generated/zod.gen";

import { isDiagnosisActive } from "./diagnosis-activity";

describe("isDiagnosisActive", () => {
  it("is active for every status except done and failed", () => {
    const active = zDiagnosisStatus.options.filter((status) => isDiagnosisActive(status));
    expect(active).toEqual(["queued", "bisecting", "verifying", "explaining"]);
  });

  it("is not active before the diagnosis loads", () => {
    expect(isDiagnosisActive(undefined)).toBe(false);
  });
});
