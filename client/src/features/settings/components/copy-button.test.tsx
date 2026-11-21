import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CopyButton } from "./copy-button";

describe("CopyButton", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("says Copied, then goes back to Copy", async () => {
    render(<CopyButton value="pip install first-domino" label="Copy terminal" />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copy terminal" }));
    });
    expect(screen.getByText("Copied")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(2_000);
    });
    expect(screen.getByText("Copy")).toBeInTheDocument();
  });
});
