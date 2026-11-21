export type OnboardingStatus = "done" | "todo" | "loading";

export type OnboardingItem = {
  id: "create_key" | "connect_agent" | "start_worker";
  status: OnboardingStatus;
};

export type OnboardingInput = {
  hasActiveKey: boolean | undefined;
  recordedRuns: number | undefined;
  replayRuns: number | undefined;
};

function statusOf(value: boolean | undefined): OnboardingStatus {
  if (value === undefined) return "loading";
  return value ? "done" : "todo";
}

function positive(count: number | undefined): boolean | undefined {
  return count === undefined ? undefined : count > 0;
}

/** The three setup steps, each ticked from the project's own data. */
export function onboardingItems({
  hasActiveKey,
  recordedRuns,
  replayRuns,
}: OnboardingInput): OnboardingItem[] {
  return [
    { id: "create_key", status: statusOf(hasActiveKey) },
    { id: "connect_agent", status: statusOf(positive(recordedRuns)) },
    { id: "start_worker", status: statusOf(positive(replayRuns)) },
  ];
}

export function doneCount(items: OnboardingItem[]): number {
  return items.filter((item) => item.status === "done").length;
}
