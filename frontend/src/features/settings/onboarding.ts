export type OnboardingStatus = "done" | "todo" | "loading";

export type OnboardingItem = {
  id: "create_key" | "install_sdk" | "record_run" | "start_worker";
  title: string;
  description: string;
  href: string;
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

export function onboardingItems({
  hasActiveKey,
  recordedRuns,
  replayRuns,
}: OnboardingInput): OnboardingItem[] {
  return [
    {
      id: "create_key",
      title: "Create an API key",
      description: "The SDK and the replay worker send it with every call.",
      href: "#api-keys",
      status: statusOf(hasActiveKey),
    },
    {
      id: "install_sdk",
      title: "Install the SDK",
      description:
        "Install first-domino where your agent runs and set the key. This ticks when your first run arrives.",
      href: "#connect",
      status: statusOf(positive(recordedRuns)),
    },
    {
      id: "record_run",
      title: "Record a first run",
      description: "Wrap your agent with fd.record. Failed runs are diagnosed automatically.",
      href: "#connect",
      status: statusOf(positive(recordedRuns)),
    },
    {
      id: "start_worker",
      title: "Start a replay worker",
      description:
        "Run fd.Worker next to your agent so diagnoses can replay it. This ticks after its first replay.",
      href: "#connect",
      status: statusOf(positive(replayRuns)),
    },
  ];
}

export function doneCount(items: OnboardingItem[]): number {
  return items.filter((item) => item.status === "done").length;
}
