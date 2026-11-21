"use client";

import { CircleCheckIcon, SearchIcon, TriangleAlertIcon } from "lucide-react";
import { notFound } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import type { Diagnosis } from "@/api/generated";
import { EmptyState } from "@/components/feedback/empty-state";
import { QueryError } from "@/components/feedback/query-error";
import { RunStepStrip } from "@/components/runs/run-step-strip";
import { defaultSelectedStep } from "@/components/runs/step-strip-state";
import { Panel } from "@/components/layout/panel";
import { Skeleton } from "@/components/ui/skeleton";
import { isDiagnosisActive } from "@/hooks/api/diagnosis-activity";
import { useGetDiagnosis } from "@/hooks/api/use-get-diagnosis";
import { useGetRun } from "@/hooks/api/use-get-run";
import { useListChecks } from "@/hooks/api/use-list-checks";
import { listStepsKey, useListSteps } from "@/hooks/api/use-list-steps";
import { isApiError } from "@/lib/api-error";

import { latestDriftToolName } from "../replay-drift";
import { canFlagRun, isJudgedByModel } from "../run-flag";
import { CheckReplays } from "../replays/check-replays";
import { CheckList } from "./check-list";
import { checkRows } from "./check-rows";
import { DiagnoseRunButton } from "./diagnose-run-button";
import { DiagnosisFailed } from "./diagnosis-failed";
import { FlagRunButton } from "./flag-run-button";
import { RunHeader } from "./run-header";
import { RunInputPanel } from "./run-input-panel";
import { RunTrace } from "./run-trace";
import { VerdictCard } from "./verdict-card";
import { VerdictHero } from "./verdict-hero";

type RunDiagnosisViewProps = { runId: string };

export function RunDiagnosisView({ runId }: RunDiagnosisViewProps) {
  const run = useGetRun(runId);
  const isRecording = run.data?.status === "running";
  const steps = useListSteps(runId, { isLive: isRecording });
  const queryClient = useQueryClient();
  const wasRecording = useRef(isRecording);

  // Steps and the run are polled apart: when the run finishes, fetch the steps once more so
  // a last step recorded just before the finish is not missed.
  useEffect(() => {
    if (wasRecording.current && !isRecording) {
      void queryClient.invalidateQueries({ queryKey: listStepsKey(runId) });
    }
    wasRecording.current = isRecording;
  }, [isRecording, queryClient, runId]);
  const [createdDiagnosisId, setCreatedDiagnosisId] = useState<string | null>(null);
  // undefined: open the default step (the first domino); null: every step closed.
  const [pickedStep, setPickedStep] = useState<number | null | undefined>(undefined);
  const [replayCheckId, setReplayCheckId] = useState<string | null>(null);

  const diagnosisId = createdDiagnosisId ?? run.data?.latest_diagnosis_id ?? null;
  const diagnosisQuery = useGetDiagnosis(diagnosisId);
  const diagnosis = diagnosisQuery.data;
  const isLive = isDiagnosisActive(diagnosis?.status);
  const checks = useListChecks(diagnosisId, { isLive: isLive || diagnosisQuery.isPending });

  useEffect(() => {
    if (replayCheckId === null) return;
    document
      .getElementById("check-replays")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [replayCheckId]);

  if (isApiError(run.error, "not_found")) notFound();

  if (run.isLoadingError) {
    return (
      <QueryError error={run.error} what="this run" source="runs.load" onRetry={run.refetch} />
    );
  }
  if (!run.data) return <RunDiagnosisSkeleton />;

  const stepCount = steps.data?.length ?? run.data.step_count;
  const selectedStep =
    pickedStep === undefined
      ? isRecording
        ? null
        : defaultSelectedStep(stepCount, diagnosis)
      : pickedStep;
  const dominoStep = steps.data?.find((step) => step.index === diagnosis?.first_domino_step);
  const rows = checkRows(checks.data ?? []);
  const replayCheck = rows.find((row) => row.id === replayCheckId);
  // A finished run with no steps has nothing to search, so it is never diagnosed.
  const hasNoSteps = !isRecording && stepCount === 0;
  const canDiagnose =
    run.data.status === "failed" && run.data.source === "recorded" && !isLive && !hasNoSteps;
  const isModelJudged = isJudgedByModel(run.data, diagnosisId);

  function handleCreated(created: Diagnosis) {
    setCreatedDiagnosisId(created.id);
    setPickedStep(undefined);
    setReplayCheckId(null);
  }

  function selectStep(step: number) {
    setPickedStep(step);
    document.getElementById(`step-${step}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const stepStrip = steps.isLoadingError ? (
    <QueryError
      error={steps.error}
      what="the steps"
      source="runs.load_steps"
      onRetry={steps.refetch}
    />
  ) : (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs text-muted-foreground">Steps</h3>
        <span className="text-xs text-muted-foreground">
          Each step is a save point. Pick one to read it.
        </span>
      </div>
      <RunStepStrip
        stepCount={stepCount}
        diagnosis={diagnosis}
        selectedStep={selectedStep}
        onSelectStep={selectStep}
      />
    </div>
  );

  return (
    <div className="flex flex-col gap-6">
      <RunHeader
        run={run.data}
        title={diagnosis?.explanation?.title}
        actions={
          canDiagnose ? (
            <DiagnoseRunButton
              runId={runId}
              hasDiagnosis={diagnosisId !== null}
              onCreated={handleCreated}
            />
          ) : (
            canFlagRun(run.data) && <FlagRunButton runId={runId} />
          )
        }
      />

      {hasNoSteps && run.data.status === "failed" ? (
        <Panel>
          <EmptyState
            icon={SearchIcon}
            title="Nothing to diagnose"
            description="This run failed without recording a step, so there is no step to blame and nothing to replay. Check that your agent's model calls happen inside the function marked with @fd.entrypoint."
          />
        </Panel>
      ) : diagnosisId === null && run.data.status !== "failed" ? (
        <Panel>
          <RunStatusNote status={run.data.status} stepCount={stepCount} />
        </Panel>
      ) : diagnosisId === null ? (
        <Panel>
          <EmptyState
            icon={SearchIcon}
            title="Not diagnosed yet"
            description={
              run.data.source === "replay"
                ? "This is a replay made while diagnosing another run. Replays are not diagnosed themselves."
                : "Diagnose this run to replay it from its save points and find the first domino."
            }
            action={
              canDiagnose && (
                <DiagnoseRunButton runId={runId} hasDiagnosis={false} onCreated={handleCreated} />
              )
            }
          />
        </Panel>
      ) : diagnosisQuery.isLoadingError ? (
        <QueryError
          error={diagnosisQuery.error}
          what="the diagnosis"
          source="runs.load_diagnosis"
          onRetry={diagnosisQuery.refetch}
        />
      ) : diagnosis ? (
        <VerdictHero diagnosis={diagnosis} checks={checks.data ?? []} isModelJudged={isModelJudged}>
          {stepStrip}
        </VerdictHero>
      ) : (
        <Skeleton className="h-48 w-full rounded-lg" />
      )}

      {!hasNoSteps && diagnosis?.status === "failed" && (
        <DiagnosisFailed
          diagnosis={diagnosis}
          driftToolName={latestDriftToolName(checks.data ?? [])}
        />
      )}
      {!hasNoSteps && diagnosis?.status === "done" && (
        <VerdictCard diagnosis={diagnosis} originalStep={dominoStep} checks={checks.data ?? []} />
      )}

      <Panel
        id="trace"
        title="Trace"
        actions={
          isRecording && (
            <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
              <span
                className="size-1.5 animate-pulse rounded-full bg-foreground"
                aria-hidden="true"
              />
              Live
            </span>
          )
        }
      >
        {steps.isLoadingError ? (
          <div className="p-4">
            <QueryError
              error={steps.error}
              what="the steps"
              source="runs.load_trace"
              onRetry={steps.refetch}
            />
          </div>
        ) : steps.data ? (
          <RunTrace
            steps={steps.data}
            selectedStep={selectedStep}
            dominoStep={diagnosis?.first_domino_step ?? null}
            isLive={isRecording}
            onSelectStep={setPickedStep}
          />
        ) : (
          <div className="p-4">
            <Skeleton className="h-40 w-full" />
          </div>
        )}
      </Panel>

      {diagnosisId !== null && !hasNoSteps && (
        <Panel
          id="checks"
          title="Checks"
          description="Each check keeps the first steps as recorded and replays the rest"
        >
          {isModelJudged && (
            <p className="border-b px-4 py-2 text-xs text-muted-foreground">
              Replays are judged by a model against this report, not by your success check.
            </p>
          )}
          {checks.isLoadingError ? (
            <div className="p-4">
              <QueryError
                error={checks.error}
                what="the checks"
                source="runs.load_checks"
                onRetry={checks.refetch}
              />
            </div>
          ) : checks.data ? (
            <CheckList
              checks={rows}
              selectedCheckId={replayCheckId}
              onViewReplays={(check) => setReplayCheckId(check.id)}
            />
          ) : (
            <div className="p-4">
              <Skeleton className="h-40 w-full" />
            </div>
          )}
        </Panel>
      )}
      {replayCheck && (
        <CheckReplays
          key={replayCheck.id}
          check={replayCheck}
          isLive={isLive}
          originalSteps={steps.data ?? []}
          onClose={() => setReplayCheckId(null)}
        />
      )}
      <RunInputPanel run={run.data} />
    </div>
  );
}

function RunDiagnosisSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true">
      <div className="flex flex-col gap-3">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-8 w-96 max-w-full" />
      </div>
      <Skeleton className="h-48 w-full rounded-lg" />
      <div className="grid gap-6 xl:grid-cols-2">
        <Skeleton className="h-56 w-full rounded-lg" />
        <Skeleton className="h-56 w-full rounded-lg" />
      </div>
    </div>
  );
}

const STATUS_NOTE = {
  running: {
    icon: null,
    title: "Recording this run",
    body: "Your agent is taking steps right now. They appear in the trace below as they happen.",
  },
  passed: {
    icon: CircleCheckIcon,
    title: "This run passed",
    body: "Your success check passed it, so there is nothing to diagnose. If it still went wrong, mark it as failed to diagnose it. Its full trace is below.",
  },
  errored: {
    icon: TriangleAlertIcon,
    title: "This run errored",
    body: "Your agent raised an error before the run could finish. The steps it took are below.",
  },
} as const;

function RunStatusNote({
  status,
  stepCount,
}: {
  status: "running" | "passed" | "errored";
  stepCount: number;
}) {
  const note = STATUS_NOTE[status];
  const Icon = note.icon;
  return (
    <div className="flex items-start gap-3 p-5">
      {Icon ? (
        <Icon
          className={
            status === "passed"
              ? "mt-0.5 size-4 text-foreground"
              : "mt-0.5 size-4 text-muted-foreground"
          }
          aria-hidden="true"
        />
      ) : (
        <span className="relative mt-1.5 flex size-2.5" aria-hidden="true">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-foreground opacity-60 motion-reduce:animate-none" />
          <span className="relative inline-flex size-2.5 rounded-full bg-foreground" />
        </span>
      )}
      <div className="flex flex-col gap-1">
        <h2 className="text-sm font-medium">{note.title}</h2>
        <p className="text-sm text-muted-foreground" aria-live="polite">
          {note.body} {status === "running" && `${stepCount} so far.`}
        </p>
      </div>
    </div>
  );
}
