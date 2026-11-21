"use client";

import { ArrowRightIcon, CheckIcon } from "lucide-react";
import Link from "next/link";

import type { CountRunsRequest } from "@/api/generated";
import { buttonVariants } from "@/components/ui/button";
import { useCountRuns } from "@/hooks/api/use-count-runs";
import { useListApiKeys } from "@/hooks/api/use-list-api-keys";
import { pageItems } from "@/lib/paging";
import { cn } from "@/lib/utils";

import { onboardingItems, type OnboardingItem } from "../onboarding";
import { apiKeyState } from "./api-key-state";
import { ApiKeys } from "./api-keys-card";
import { CodeBlock } from "./code-block";

const RECORDED_RUNS: CountRunsRequest = { sources: ["recorded"] };
const REPLAY_RUNS: CountRunsRequest = { sources: ["replay"] };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const INSTALL_SNIPPET = `pip install "first-domino[openai] @ git+https://github.com/saiabhiramjaini/first-domino#subdirectory=server/packages/first-domino"

export FIRST_DOMINO_API_KEY=fd_live_...   # the key from step 1
export FIRST_DOMINO_BASE_URL=${API_URL}`;

const RECORD_SNIPPET = `import first_domino as fd
from openai import AsyncOpenAI

openai = AsyncOpenAI()

async def handle(task_text: str, task_id: str) -> None:
    task = fd.TaskInput(prompt=task_text, metadata={"task_id": task_id})
    async with fd.record("call-assistant", task) as run:
        client = fd.wrap(openai, run)          # every model turn becomes a step
        result = await run_agent(client, task) # your agent, unchanged
        outcome = fd.RunOutcome.passed if check(result) else fd.RunOutcome.failed
        await run.finish(outcome, final_output=result.summary)`;

const WORKER_SNIPPET = `worker = fd.Worker(agent_names=["call-assistant"])

@worker.agent("call-assistant")
async def replay(ctx: fd.ReplayContext):
    # Continue from ctx.messages; use ctx.replacement_output as the next turn when set.
    return await continue_agent(fd.messages_to_openai(ctx.messages), ctx)

@worker.success_check("call-assistant")
def check_replay(task_input: fd.TaskInput, result) -> bool:
    return check(result)

await worker.run()   # only connects outward; your code and secrets stay with you`;

type StepState = "done" | "current" | "todo";

const STEP_COPY = {
  create_key: {
    title: "Create an API key",
    body: "The SDK and the replay worker send it with every call. Give each agent or machine its own.",
  },
  install_sdk: {
    title: "Install the SDK",
    body: "Install first-domino where your agent runs and set the key.",
  },
  record_run: {
    title: "Record your runs",
    body: "Wrap the agent you already have. A run your check marks failed is diagnosed automatically.",
  },
  start_worker: {
    title: "Start the replay worker",
    body: "Run it next to your agent so diagnoses can replay it from any step.",
  },
} as const satisfies Record<OnboardingItem["id"], { title: string; body: string }>;

function stepContent(id: OnboardingItem["id"]): React.ReactNode {
  switch (id) {
    case "create_key":
      return <ApiKeys />;
    case "install_sdk":
      return <CodeBlock label="Terminal" code={INSTALL_SNIPPET} />;
    case "record_run":
      return <CodeBlock label="agent.py" code={RECORD_SNIPPET} />;
    case "start_worker":
      return <CodeBlock label="worker.py" code={WORKER_SNIPPET} />;
  }
}

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
        "relative z-10 flex size-8 shrink-0 items-center justify-center rounded-full border font-mono text-xs font-medium",
        state === "done" && "border-verified/40 bg-verified/15 text-verified",
        state === "current" &&
          "border-domino bg-domino text-domino-foreground shadow-[0_0_0_4px_color-mix(in_oklch,var(--domino),transparent_80%)]",
        state === "todo" && "border-border bg-card text-muted-foreground"
      )}
    >
      {state === "done" ? <CheckIcon className="size-4" aria-hidden="true" /> : number}
    </span>
  );
}

const STATE_LABEL = { done: "Done", current: "Next", todo: "Later" } as const;

// Setup as one timeline: each step ticks itself from the project's own data.
export function SetupTimeline() {
  const apiKeys = useListApiKeys();
  const recordedRuns = useCountRuns(RECORDED_RUNS);
  const replayRuns = useCountRuns(REPLAY_RUNS);
  const items = onboardingItems({
    hasActiveKey: apiKeys.data
      ? pageItems(apiKeys.data).some((apiKey) => apiKeyState(apiKey) === "active")
      : undefined,
    recordedRuns: recordedRuns.data,
    replayRuns: replayRuns.data,
  });
  const states = stepStates(items);
  const isComplete = states.every((state) => state === "done");

  return (
    <ol className="relative flex flex-col" aria-label="Set up your agent">
      {items.map((item, index) => {
        const state = states[index] ?? "todo";
        const copy = STEP_COPY[item.id];
        return (
          <li key={item.id} id={item.id} className="relative flex scroll-mt-20 gap-5 pb-10">
            <span
              className={cn(
                "absolute top-8 bottom-0 left-4 w-px -translate-x-1/2",
                state === "done" ? "bg-verified/40" : "bg-border"
              )}
              aria-hidden="true"
            />
            <Marker state={state} number={index + 1} />
            <div className="flex min-w-0 flex-1 flex-col gap-4 pt-1">
              <div className="flex flex-col gap-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-semibold">{copy.title}</h2>
                  <span
                    className={cn(
                      "text-[11px] font-medium tracking-wider uppercase",
                      state === "done" && "text-verified",
                      state === "current" && "text-domino",
                      state === "todo" && "text-muted-foreground"
                    )}
                  >
                    {STATE_LABEL[state]}
                  </span>
                </div>
                <p className="max-w-2xl text-sm text-pretty text-muted-foreground">{copy.body}</p>
              </div>
              {stepContent(item.id)}
            </div>
          </li>
        );
      })}
      <li className="relative flex gap-5">
        <span
          className={cn(
            "relative z-10 flex size-8 shrink-0 items-center justify-center rounded-full border",
            isComplete ? "border-verified/40 bg-verified/15 text-verified" : "border-dashed bg-card"
          )}
          aria-hidden="true"
        >
          {isComplete && <CheckIcon className="size-4" />}
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-3 pt-1">
          <div className="flex flex-col gap-1">
            <h2 className="font-semibold">
              {isComplete ? "You're set up" : "Watch failures arrive"}
            </h2>
            <p className="max-w-2xl text-sm text-pretty text-muted-foreground">
              Every failed run shows up in Failures with its first domino, usually within a minute.
            </p>
          </div>
          <Link
            href="/failures"
            className={buttonVariants({
              variant: isComplete ? "brand" : "outline",
              className: "self-start",
            })}
          >
            Open Failures
            <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
          </Link>
        </div>
      </li>
    </ol>
  );
}
