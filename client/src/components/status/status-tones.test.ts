import { describe, expect, it } from "vitest";

import {
  zCheckPhase,
  zCheckResult,
  zDiagnosisStatus,
  zRunStatus,
  zVerdictKind,
} from "@/api/generated/zod.gen";

import {
  CHECK_PHASE,
  CHECK_RESULT,
  DIAGNOSIS_STATUS,
  RUN_STATUS,
  VERDICT_KIND,
} from "./status-tones";
import { TONE_BADGE_VARIANT } from "./tone";

describe("status tone maps", () => {
  it("cover every contract value with a known tone", () => {
    const maps = [
      [zRunStatus.options, RUN_STATUS],
      [zDiagnosisStatus.options, DIAGNOSIS_STATUS],
      [zVerdictKind.options, VERDICT_KIND],
      [zCheckResult.options, CHECK_RESULT],
      [zCheckPhase.options, CHECK_PHASE],
    ] as const;
    for (const [values, map] of maps) {
      for (const value of values) {
        const entry: { tone: keyof typeof TONE_BADGE_VARIANT; label: string } | undefined =
          Object.entries(map).find(([key]) => key === value)?.[1];
        expect(entry, value).toBeDefined();
        expect(TONE_BADGE_VARIANT[entry?.tone ?? "neutral"]).toBeTruthy();
      }
    }
  });

  it("keeps failure red and success green", () => {
    expect(RUN_STATUS.failed.tone).toBe("danger");
    expect(RUN_STATUS.passed.tone).toBe("success");
    expect(VERDICT_KIND.step_verified.tone).toBe("success");
  });
});
