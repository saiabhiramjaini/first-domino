import { describe, expect, it } from "vitest";

import { shortId, verifiedLabel, verifyPassesLabel } from "./cause-stats";

describe("cause stats", () => {
  it("labels verified runs out of all runs", () => {
    expect(verifiedLabel(3, 5)).toBe("3 of 5 verified");
  });

  it("labels verify passes, or says verify did not run", () => {
    expect(verifyPassesLabel(4, 5)).toBe("4 of 5");
    expect(verifyPassesLabel(null, null)).toBe("Not run");
  });

  it("shortens an id for display", () => {
    expect(shortId("7b0f7c55-8d0e-4a52-9a43-0c8f3f1f2a10")).toBe("7b0f7c55");
  });
});
