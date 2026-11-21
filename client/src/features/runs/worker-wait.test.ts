import { describe, expect, it } from "vitest";

import { isWaitingForWorker, waitedText } from "./worker-wait";

const NOW = new Date("2026-11-21T12:00:00Z");

describe("isWaitingForWorker", () => {
  it("is true once queued replays wait past the notice time", () => {
    expect(
      isWaitingForWorker(
        { status: "bisecting", replays_waiting: 3, waiting_since: "2026-11-21T11:58:00Z" },
        NOW
      )
    ).toBe(true);
  });

  it("stays quiet for a short wait, when nothing waits, or once the diagnosis is over", () => {
    expect(
      isWaitingForWorker(
        { status: "bisecting", replays_waiting: 3, waiting_since: "2026-11-21T11:59:55Z" },
        NOW
      )
    ).toBe(false);
    expect(
      isWaitingForWorker({ status: "bisecting", replays_waiting: 0, waiting_since: null }, NOW)
    ).toBe(false);
    expect(
      isWaitingForWorker(
        { status: "done", replays_waiting: 3, waiting_since: "2026-11-21T11:00:00Z" },
        NOW
      )
    ).toBe(false);
  });
});

describe("waitedText", () => {
  it("uses seconds, then minutes", () => {
    expect(waitedText(45_000)).toBe("45 seconds");
    expect(waitedText(150_000)).toBe("3 minutes");
  });
});
