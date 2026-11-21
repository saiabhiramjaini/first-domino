import { describe, expect, it } from "vitest";

import { runDuration } from "./run-duration";

describe("runDuration", () => {
  it("measures a finished run from start to finish", () => {
    expect(runDuration("2026-11-21T10:00:00Z", "2026-11-21T10:00:12.4Z", new Date())).toBe(
      "12.4 sec"
    );
  });

  it("measures a running run up to now", () => {
    expect(runDuration("2026-11-21T10:00:00Z", null, new Date("2026-11-21T10:00:03Z"))).toBe(
      "3 sec"
    );
  });
});
