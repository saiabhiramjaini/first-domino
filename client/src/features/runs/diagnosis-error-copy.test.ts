import { describe, expect, it } from "vitest";

import { zDiagnosisErrorCode } from "@/api/generated/zod.gen";

import { diagnosisErrorCopy } from "./diagnosis-error-copy";

describe("diagnosisErrorCopy", () => {
  it("has a title and a fix for every error code", () => {
    for (const code of zDiagnosisErrorCode.options) {
      const copy = diagnosisErrorCopy(code);
      expect(copy.title, code).toBeTruthy();
      expect(copy.fix, code).toBeTruthy();
    }
  });

  it("points a missing worker to fd.Worker", () => {
    expect(diagnosisErrorCopy("replay_unavailable").fix).toContain("fd.Worker");
  });

  it("falls back when the code is missing", () => {
    expect(diagnosisErrorCopy(null).title).toContain("stopped");
  });
});
