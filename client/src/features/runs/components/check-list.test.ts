import { describe, expect, it } from "vitest";

import { savePointText } from "./check-list";

describe("savePointText", () => {
  it("describes what a bisect check keeps", () => {
    expect(savePointText("precheck", 0)).toBe("Fresh run");
    expect(savePointText("bisect", 1)).toBe("Keep step 1");
    expect(savePointText("bisect", 7)).toBe("Keep steps 1 to 7");
  });

  it("names the fixed step a verify or fallback check replays", () => {
    expect(savePointText("verify", 5)).toBe("Keep steps 1 to 5, then fixed step 6");
    expect(savePointText("fallback", 0)).toBe("Fixed step 1");
  });

  it("says a calibrate check keeps every recorded step", () => {
    expect(savePointText("calibrate", 12)).toBe("Keep all 12 steps");
    expect(savePointText("calibrate", 1)).toBe("Keep the only step");
  });
});
