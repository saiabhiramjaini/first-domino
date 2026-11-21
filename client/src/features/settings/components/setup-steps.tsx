"use client";

import { ArrowDownIcon, ArrowRightIcon, CheckIcon } from "lucide-react";
import Link from "next/link";

import type { CountRunsRequest } from "@/api/generated";
import { buttonVariants } from "@/components/ui/button";
import { useCountRuns } from "@/hooks/api/use-count-runs";
import { useListApiKeys } from "@/hooks/api/use-list-api-keys";
import { pageItems } from "@/lib/paging";
import { cn } from "@/lib/utils";

import { doneCount, onboardingItems, type OnboardingItem } from "../onboarding";
import { apiKeyState } from "./api-key-state";
import { CodeBlock } from "./code-block";

const RECORDED_RUNS: CountRunsRequest = { sources: ["recorded"] };
const REPLAY_RUNS: CountRunsRequest = { sources: ["replay"] };
// The steps tick themselves, so keep the counts fresh while someone is setting up.
const REFRESH_MS = 5_000;

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const INSTALL_SNIPPET = `pip install "first-domino @ git+https://github.com/saiabhiramjaini/first-domino#subdirectory=server/packages/first-domino"

export FIRST_DOMINO_API_KEY=fd_live_...
export FIRST_DOMINO_BASE_URL=${API_URL}`;

const AGENT_SNIPPET = `import first_domino as fd

@fd.entrypoint("support-bot", check=lambda question, answer: "refund" in answer)
def answer(question: str) -> str:
    ...  # your agent, unchanged

@fd.tool  # optional: a tool with side effects is never repeated in a replay
def send_refund(order_id: str, amount: float) -> str:
    ...`;

const WORKER_SNIPPET = `import first_domino as fd
import my_agent  # the module with your @fd.entrypoint

fd.serve()  # connects outward only; your code and keys stay with you`;

const FRAMEWORKS = [
  "OpenAI",
  "Anthropic",
  "LangChain",
  "OpenAI Agents SDK",
  "OpenAI-compatible APIs",
];

type StepState = "done" | "current" | "todo";

const STEP_COPY = {
  create_key: {
    title: "Create an API key",
    body: "The SDK and the replay worker send it with every call.",
    waiting: "",
  },
  connect_agent: {
    title: "Add two lines to your agent",
    body: "Mark the function that runs your agent. Every model call inside it is recorded live, and check decides pass or fail. Failed runs are diagnosed on their own.",
    waiting: "Waiting for your first run",
  },
  start_worker: {
    title: "Start the replay worker",
    body: "Run it next to your agent with the same code and keys. First Domino asks it to replay runs from any step.",
    waiting: "Waiting for the first replay",
  },
} as const satisfies Record<OnboardingItem["id"], { title: string; body: string; waiting: string }>;

function stepStates(items: OnboardingItem[]): StepState[] {
  const current = items.findIndex((item) => item.status !== "done");
  return items.map((item, index) =>
    item.status === "done" ? "done" : index === current ? "current" : "todo"
  );
}

function Marker({ state, number }: { state: StepState; number: number }) {
  return (
    <span
      className={cn(
        "relative z-10 flex size-6 shrink-0 items-center justify-center rounded-full border text-xs font-medium tabular-nums",
        state === "done" && "border-border bg-muted text-foreground",
        state === "current" && "border-foreground bg-foreground text-background",
        state === "todo" && "border-border bg-background text-muted-foreground"
      )}
    >
      {state === "done" ? <CheckIcon className="size-3.5" aria-hidden="true" /> : number}
    </span>
  );
}

function StepStatus({ state, waiting }: { state: StepState; waiting: string }) {
  if (state === "done") return <span className="text-xs text-muted-foreground">Done</span>;
  if (state === "todo" || !waiting) return null;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <span className="relative flex size-1.5" aria-hidden="true">
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-foreground opacity-50 motion-reduce:animate-none" />
        <span className="relative inline-flex size-1.5 rounded-full bg-foreground" />
      </span>
      {waiting}
    </span>
  );
}

function stepContent(id: OnboardingItem["id"], state: StepState): React.ReactNode {
  switch (id) {
    case "create_key":
      return state === "done" ? null : (
        <a
          href="#api-keys"
          className={buttonVariants({ variant: "outline", size: "sm", className: "self-start" })}
        >
          Create a key
          <ArrowDownIcon data-icon="inline-end" aria-hidden="true" />
        </a>
      );
    case "connect_agent":
      return (
        <div className="flex flex-col gap-3">
          <CodeBlock label="terminal" code={INSTALL_SNIPPET} />
          <CodeBlock label="agent.py" code={AGENT_SNIPPET} />
          <p className="text-xs text-muted-foreground">
            Works with {FRAMEWORKS.join(", ")}: sync or async, streaming or not.
          </p>
        </div>
      );
    case "start_worker":
      return <CodeBlock label="worker.py" code={WORKER_SNIPPET} />;
  }
}

// Setup as three steps; each ticks itself as soon as First Domino sees it working.
export function SetupSteps() {
  const apiKeys = useListApiKeys();
  const recordedRuns = useCountRuns(RECORDED_RUNS, { refreshMs: REFRESH_MS });
  const replayRuns = useCountRuns(REPLAY_RUNS, { refreshMs: REFRESH_MS });
  const items = onboardingItems({
    hasActiveKey: apiKeys.data
      ? pageItems(apiKeys.data).some((apiKey) => apiKeyState(apiKey) === "active")
      : undefined,
    recordedRuns: recordedRuns.data,
    replayRuns: replayRuns.data,
  });
  const states = stepStates(items);
  const isComplete = doneCount(items) === items.length;

  return (
    <div className="flex flex-col gap-6">
      <ol className="flex flex-col" aria-label="Set up your agent">
        {items.map((item, index) => {
          const state = states[index] ?? "todo";
          const copy = STEP_COPY[item.id];
          const isLast = index === items.length - 1;
          return (
            <li
              key={item.id}
              id={item.id}
              className="relative flex scroll-mt-20 gap-4 pb-8 last:pb-0"
            >
              {!isLast && (
                <span
                  className="absolute top-7 bottom-1 left-3 w-px bg-border"
                  aria-hidden="true"
                />
              )}
              <Marker state={state} number={index + 1} />
              <div className="flex min-w-0 flex-1 flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                    <h3 className="text-sm font-medium">{copy.title}</h3>
                    <StepStatus state={state} waiting={copy.waiting} />
                  </div>
                  <p className="max-w-2xl text-sm text-pretty text-muted-foreground">{copy.body}</p>
                </div>
                {stepContent(item.id, state)}
              </div>
            </li>
          );
        })}
      </ol>
      {isComplete && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border px-4 py-3">
          <p className="text-sm">
            You are set up. Failed runs are diagnosed on their own, usually within a minute.
          </p>
          <Link href="/runs?status=failed" className={buttonVariants({ size: "sm" })}>
            See failed runs
            <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
          </Link>
        </div>
      )}
    </div>
  );
}
