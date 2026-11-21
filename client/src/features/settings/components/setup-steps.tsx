"use client";

import {
  ArrowRightIcon,
  CheckIcon,
  KeyRoundIcon,
  PlugIcon,
  RotateCcwIcon,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useState, useSyncExternalStore } from "react";

import type { CountRunsRequest } from "@/api/generated";
import { Button, buttonVariants } from "@/components/ui/button";
import { useCountRuns } from "@/hooks/api/use-count-runs";
import { useListApiKeys } from "@/hooks/api/use-list-api-keys";
import { pageItems } from "@/lib/paging";
import { cn } from "@/lib/utils";

import { doneCount, onboardingItems, type OnboardingItem } from "../onboarding";
import { apiKeyState } from "./api-key-state";
import { ApiKeySecretDialog } from "./api-key-secret-dialog";
import { ApiKeys, type CreatedApiKey } from "./api-keys-card";
import { CodeBlock } from "./code-block";

const RECORDED_RUNS: CountRunsRequest = { sources: ["recorded"] };
const REPLAY_RUNS: CountRunsRequest = { sources: ["replay"] };
// The steps tick themselves, so keep the counts fresh while someone is setting up.
const REFRESH_MS = 5_000;

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const INSTALL_SNIPPET = `pip install first-domino   # or: uv add first-domino

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

type StepState = "done" | "current" | "todo";

const STEP_COPY = {
  create_key: {
    label: "API key",
    title: "Create an API key",
    body: "The SDK and the replay worker send it with every call. Give each agent or machine its own key, so you can revoke one alone.",
    waiting: "",
  },
  connect_agent: {
    label: "Connect your agent",
    title: "Add two lines to your agent",
    body: "Mark the function that runs your agent. Every model call inside it is recorded live. Works with OpenAI, Anthropic, LangChain and the OpenAI Agents SDK.",
    waiting: "Waiting for your first run",
  },
  start_worker: {
    label: "Replay worker",
    title: "Start the replay worker",
    body: "Run it next to your agent with the same code and keys, so failed runs can be replayed from any step.",
    waiting: "Waiting for the first replay",
  },
} as const satisfies Record<
  OnboardingItem["id"],
  { label: string; title: string; body: string; waiting: string }
>;

function stepStates(items: OnboardingItem[]): StepState[] {
  const current = items.findIndex((item) => item.status !== "done");
  return items.map((item, index) =>
    item.status === "done" ? "done" : index === current ? "current" : "todo"
  );
}

const STEP_ICON = {
  create_key: KeyRoundIcon,
  connect_agent: PlugIcon,
  start_worker: RotateCcwIcon,
} as const satisfies Record<OnboardingItem["id"], LucideIcon>;

// Each step has its own icon. A finished step is filled in; the others are outlined.
function Marker({
  id,
  state,
  isPicked,
}: {
  id: OnboardingItem["id"];
  state: StepState;
  isPicked: boolean;
}) {
  const Icon = STEP_ICON[id];
  return (
    <span
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-full border transition-colors",
        state === "done" && "border-transparent bg-foreground text-background",
        state !== "done" && isPicked && "border-foreground bg-background text-foreground",
        state !== "done" && !isPicked && "border-border bg-background text-muted-foreground"
      )}
    >
      <Icon className="size-4" aria-hidden="true" />
    </span>
  );
}

function Waiting({ text }: { text: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <span className="relative flex size-1.5" aria-hidden="true">
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-foreground opacity-50 motion-reduce:animate-none" />
        <span className="relative inline-flex size-1.5 rounded-full bg-foreground" />
      </span>
      {text}
    </span>
  );
}

function stepContent(
  id: OnboardingItem["id"],
  onKeyCreated: (createdKey: CreatedApiKey) => void
): React.ReactNode {
  switch (id) {
    case "create_key":
      return <ApiKeys onCreated={onKeyCreated} />;
    case "connect_agent":
      return (
        <>
          <CodeBlock label="terminal" code={INSTALL_SNIPPET} wrap />
          <CodeBlock label="agent.py" code={AGENT_SNIPPET} />
        </>
      );
    case "start_worker":
      return <CodeBlock label="worker.py" code={WORKER_SNIPPET} />;
  }
}

function subscribeToHash(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

function readHash(): string {
  return window.location.hash;
}

export function useSetupProgress() {
  const apiKeys = useListApiKeys();
  const recordedRuns = useCountRuns(RECORDED_RUNS, { refreshMs: REFRESH_MS });
  const replayRuns = useCountRuns(REPLAY_RUNS, { refreshMs: REFRESH_MS });
  return onboardingItems({
    hasActiveKey: apiKeys.data
      ? pageItems(apiKeys.data).some((apiKey) => apiKeyState(apiKey) === "active")
      : undefined,
    recordedRuns: recordedRuns.data,
    replayRuns: replayRuns.data,
  });
}

// Setup as a 1-2-3 stepper. The picked step's instructions open below it. Each step ticks
// itself as soon as First Domino sees it working.
export function SetupSteps() {
  const items = useSetupProgress();
  const states = stepStates(items);
  const isLoading = items.some((item) => item.status === "loading");
  const isComplete = doneCount(items) === items.length;
  const [pickedIndex, setPickedIndex] = useState<number | null>(null);
  // Lives here, not inside step 1: creating a key ticks step 1, and the panel below may then
  // change. The one-time secret must survive that.
  const [createdKey, setCreatedKey] = useState<CreatedApiKey | null>(null);

  function handleKeyCreated(key: CreatedApiKey) {
    setCreatedKey(key);
    setPickedIndex(0); // stay on step 1 until the person moves on
  }

  // A link such as /settings#start_worker opens that step, until another step is clicked.
  const hash = useSyncExternalStore(subscribeToHash, readHash, () => "");
  const hashIndex = items.findIndex((step) => `#${step.id}` === hash);
  const current = states.indexOf("current");
  const picked = pickedIndex ?? (hashIndex !== -1 ? hashIndex : current === -1 ? 0 : current);
  const item = items[picked];
  const state = states[picked] ?? "todo";
  if (!item) return null;
  const copy = STEP_COPY[item.id];
  const next = items[picked + 1];

  return (
    <div className="overflow-hidden rounded-lg border">
      <ol className="grid grid-cols-3 border-b" aria-label="Setup steps">
        {items.map((step, index) => {
          const stepState = states[index] ?? "todo";
          const isPicked = index === picked;
          const isLast = index === items.length - 1;
          return (
            <li key={step.id} className="relative">
              {!isLast && (
                <span
                  className={cn(
                    "absolute top-8 left-1/2 h-px w-full",
                    stepState === "done" ? "bg-foreground" : "bg-border"
                  )}
                  aria-hidden="true"
                />
              )}
              <Button
                variant="ghost"
                aria-current={isPicked ? "step" : undefined}
                onClick={() => setPickedIndex(index)}
                className={cn(
                  "relative h-auto w-full flex-col gap-2 rounded-none px-2 pt-4 pb-3 font-normal hover:bg-muted/40",
                  isPicked && "bg-muted/40"
                )}
              >
                <Marker id={step.id} state={stepState} isPicked={isPicked} />
                <span
                  className={cn(
                    "text-center text-xs text-wrap sm:text-sm",
                    isPicked || stepState === "done" ? "text-foreground" : "text-muted-foreground"
                  )}
                >
                  {STEP_COPY[step.id].label}
                </span>
              </Button>
              {isPicked && (
                <span
                  className="absolute inset-x-0 bottom-0 h-0.5 bg-foreground"
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>

      <section aria-labelledby="setup-step-title" className="flex flex-col gap-4 p-4 sm:p-5">
        <div className="flex flex-col gap-1">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <h3 id="setup-step-title" className="text-sm font-medium">
              {picked + 1}. {copy.title}
            </h3>
            {!isLoading && state === "done" && (
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <CheckIcon className="size-3.5" aria-hidden="true" />
                Done
              </span>
            )}
            {!isLoading && state === "current" && copy.waiting && <Waiting text={copy.waiting} />}
          </div>
          <p className="max-w-2xl text-sm text-pretty text-muted-foreground">{copy.body}</p>
        </div>
        <div className="flex flex-col gap-3">{stepContent(item.id, handleKeyCreated)}</div>
        {next && (
          <div className="flex justify-end">
            <Button variant="outline" size="sm" onClick={() => setPickedIndex(picked + 1)}>
              Next: {STEP_COPY[next.id].label}
              <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
            </Button>
          </div>
        )}
      </section>

      <ApiKeySecretDialog createdKey={createdKey} onClose={() => setCreatedKey(null)} />

      {isComplete && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t bg-card px-4 py-3 sm:px-5">
          <p className="text-sm text-muted-foreground">
            All set. Failed runs are diagnosed on their own, usually within a minute.
          </p>
          <Link
            href="/runs?status=failed"
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            See failed runs
            <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
          </Link>
        </div>
      )}
    </div>
  );
}

export function SetupProgress() {
  const items = useSetupProgress();
  if (items.some((item) => item.status === "loading")) return null;
  return (
    <span className="shrink-0 text-xs whitespace-nowrap text-muted-foreground tabular-nums">
      {doneCount(items)} of {items.length} done
    </span>
  );
}
