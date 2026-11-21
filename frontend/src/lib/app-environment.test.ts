import { describe, expect, it } from "vitest";

import { appEnvironment } from "./app-environment";

describe("appEnvironment", () => {
  it("keeps a known environment", () => {
    expect(appEnvironment("prod")).toBe("prod");
  });

  it("falls back to local for a missing or unknown value", () => {
    expect(appEnvironment(undefined)).toBe("local");
    expect(appEnvironment("staging")).toBe("local");
  });
});
