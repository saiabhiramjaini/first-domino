import { describe, expect, it } from "vitest";

import { zDiagnosisErrorCode } from "@/api/generated/zod.gen";

import { diagnosisErrorCopy } from "./diagnosis-error-copy";

const NO_DRIFT = { driftToolName: null };

describe("diagnosisErrorCopy", () => {
  it("has a title and a fix for every error code", () => {
    for (const code of zDiagnosisErrorCode.options) {
      const copy = diagnosisErrorCopy(code, NO_DRIFT);
      expect(copy.title, code).toBeTruthy();
      expect(copy.fix, code).toBeTruthy();
    }
  });

  it("points a missing worker to fd.Worker", () => {
    expect(diagnosisErrorCopy("replay_unavailable", NO_DRIFT).fix).toContain("fd.Worker");
  });

  it("blames the success check, not a step, when it passes the recorded run", () => {
    const copy = diagnosisErrorCopy("check_inconsistent", NO_DRIFT);
    expect(copy.title).toBe("Your success check passed the recorded run");
    expect(copy.fix).toContain("No step can be blamed");
    expect(copy.code).toBeUndefined();
  });

  it("names the drifted tool and shows the @fd.tool fix", () => {
    const copy = diagnosisErrorCopy("replay_not_faithful", { driftToolName: "lookup_order" });
    expect(copy.fix).toMatch(/^lookup_order returned different data/);
    expect(copy.fix).toContain("@fd.tool");
    expect(copy.code).toBe("@fd.tool\ndef lookup_order(...): ...");
  });

  it("still shows the @fd.tool fix when the drifted tool is unknown", () => {
    const copy = diagnosisErrorCopy("replay_not_faithful", NO_DRIFT);
    expect(copy.fix).toMatch(/^A tool returned different data/);
    expect(copy.code).toBe("@fd.tool\ndef your_tool(...): ...");
  });

  it("falls back when the code is missing", () => {
    expect(diagnosisErrorCopy(null, NO_DRIFT).title).toContain("stopped");
  });
});
