import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useSyncExternalStore } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiKey } from "@/api/generated";

import { SetupSteps } from "./setup-steps";

const SECRET = "fd_live_shown_only_once";

// A live key list, like the real query: a change re-renders every component that reads it.
let keys: ApiKey[] = [];
const listeners = new Set<() => void>();
function setKeys(next: ApiKey[]) {
  keys = next;
  for (const listener of listeners) listener();
}
function useKeys(): ApiKey[] {
  return useSyncExternalStore(
    (onChange) => {
      listeners.add(onChange);
      return () => listeners.delete(onChange);
    },
    () => keys
  );
}

const activeKey: ApiKey = {
  id: "00000000-0000-4000-8000-000000000001",
  name: "prod agents",
  prefix: "fd_live_abcd",
  created_at: "2026-11-21T00:00:00Z",
  last_used_at: null,
  revoked_at: null,
} as ApiKey;

vi.mock("@/hooks/api/use-list-api-keys", () => ({
  useListApiKeys: () => ({
    data: { pages: [{ items: useKeys(), next_cursor: null }], pageParams: [null] },
    isPending: false,
    isError: false,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: vi.fn(),
    refetch: vi.fn(),
  }),
}));

vi.mock("@/hooks/api/use-count-runs", () => ({
  useCountRuns: () => ({ data: 0 }),
}));

vi.mock("@/hooks/api/use-revoke-api-key", () => ({
  useRevokeApiKey: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

// Creating a key also changes the key list, the way the real mutation's refetch does:
// by the next render step 1 counts as done.
vi.mock("@/hooks/api/use-create-api-key", () => ({
  useCreateApiKey: () => ({
    isPending: false,
    mutateAsync: async () => {
      setKeys([activeKey]);
      return { api_key: activeKey, secret: SECRET };
    },
  }),
}));

describe("SetupSteps", () => {
  beforeEach(() => {
    keys = [];
    listeners.clear();
  });

  it("keeps the new key's secret on screen after step 1 ticks itself", async () => {
    render(<SetupSteps />);

    fireEvent.change(screen.getByLabelText("Key name"), { target: { value: "prod agents" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Create API key" }));
    });

    await waitFor(() => expect(screen.getByText(SECRET)).toBeInTheDocument());
    // Still on step 1, not moved on to step 2 (the popup hides the page from the accessibility tree).
    expect(
      screen.getByRole("heading", { name: /Create an API key/, hidden: true })
    ).toBeInTheDocument();
  });
});
