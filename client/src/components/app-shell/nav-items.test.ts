import { describe, expect, it } from "vitest";

import { NAV_ITEMS, isNavItemActive } from "./nav-items";

function activeLabels(pathname: string): string[] {
  return NAV_ITEMS.filter((item) => isNavItemActive(item, pathname)).map((item) => item.label);
}

describe("isNavItemActive", () => {
  it("marks the matching section and its children", () => {
    expect(activeLabels("/causes")).toEqual(["Root causes"]);
    expect(activeLabels("/causes/123")).toEqual(["Root causes"]);
  });

  it("keeps Runs active on a run page", () => {
    expect(activeLabels("/runs")).toEqual(["Runs"]);
    expect(activeLabels("/runs/abc")).toEqual(["Runs"]);
  });

  it("does not match a path that only shares a prefix", () => {
    expect(activeLabels("/settingsx")).toEqual([]);
  });
});
