import { describe, expect, it } from "vitest";

import { prettyJson } from "./pretty-json";

describe("prettyJson", () => {
  it("indents JSON objects and lists", () => {
    expect(prettyJson('{"a":1}')).toEqual({ text: '{\n  "a": 1\n}', isJson: true });
  });

  it("leaves plain text and bare JSON values alone", () => {
    expect(prettyJson("I refunded $20.")).toEqual({ text: "I refunded $20.", isJson: false });
    expect(prettyJson("42")).toEqual({ text: "42", isJson: false });
  });
});
