import { describe, expect, it } from "vitest";

import { exportFileBody, exportFileName } from "./export-file";

const causeExport = {
  cause_id: "88a0808b-955f-46d2-abfe-35cce9960873",
  exported_at: "2026-11-21T10:15:00Z",
  cases: [],
};

describe("export file", () => {
  it("names the file after the cause and the export date", () => {
    expect(exportFileName(causeExport)).toBe(
      "first-domino-regression-tests-88a0808b-2026-11-21.json"
    );
  });

  it("writes readable JSON that parses back to the export", () => {
    const body = exportFileBody(causeExport);
    expect(body.endsWith("\n")).toBe(true);
    expect(JSON.parse(body)).toEqual(causeExport);
  });
});
