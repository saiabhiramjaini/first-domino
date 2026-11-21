"use client";

import { CheckCircle2Icon, CircleIcon, LoaderCircleIcon, type LucideIcon } from "lucide-react";

import type { CountRunsRequest } from "@/api/generated";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useCountRuns } from "@/hooks/api/use-count-runs";
import { useListApiKeys } from "@/hooks/api/use-list-api-keys";
import { pageItems } from "@/lib/paging";
import { cn } from "@/lib/utils";

import { doneCount, onboardingItems, type OnboardingStatus } from "../onboarding";
import { apiKeyState } from "./api-key-state";

const RECORDED_RUNS: CountRunsRequest = { sources: ["recorded"] };
const REPLAY_RUNS: CountRunsRequest = { sources: ["replay"] };

const STATUS_ICON = {
  done: { icon: CheckCircle2Icon, className: "text-verified", label: "Done" },
  todo: { icon: CircleIcon, className: "text-muted-foreground", label: "Not done yet" },
  loading: {
    icon: LoaderCircleIcon,
    className: "animate-spin text-muted-foreground motion-reduce:animate-none",
    label: "Checking",
  },
} as const satisfies Record<
  OnboardingStatus,
  { icon: LucideIcon; className: string; label: string }
>;

export function OnboardingChecklist() {
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
  const done = doneCount(items);

  return (
    <Card id="get-started" className="scroll-mt-20">
      <CardHeader>
        <CardTitle>Get started</CardTitle>
        <CardDescription>
          {done === items.length
            ? "You are set up. Failed runs from your agent are diagnosed automatically."
            : `${done} of ${items.length} done. Each item ticks itself from your project's data.`}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ol className="flex flex-col gap-1">
          {items.map((item) => {
            const status = STATUS_ICON[item.status];
            const Icon = status.icon;
            return (
              <li key={item.id}>
                <a
                  href={item.href}
                  className="flex items-start gap-3 rounded-lg p-2 outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  <Icon className={cn("mt-0.5 size-4 shrink-0", status.className)} aria-hidden />
                  <span className="flex flex-col gap-0.5">
                    <span
                      className={cn(
                        "text-sm font-medium",
                        item.status === "done" && "text-muted-foreground line-through"
                      )}
                    >
                      {item.title}
                      <span className="sr-only">, {status.label}</span>
                    </span>
                    <span className="text-xs text-muted-foreground">{item.description}</span>
                  </span>
                </a>
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
