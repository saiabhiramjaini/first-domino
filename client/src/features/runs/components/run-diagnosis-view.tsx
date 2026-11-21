"use client";

import { SearchIcon } from "lucide-react";
import { notFound } from "next/navigation";
import { useEffect, useState } from "react";

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
import { useListSteps } from "@/hooks/api/use-list-steps";
import { isApiError } from "@/lib/api-error";

import { CheckReplays } from "../replays/check-replays";
import { CheckList } from "./check-list";
import { DiagnoseRunButton } from "./diagnose-run-button";
import { DiagnosisFailed } from "./diagnosis-failed";
import { RunHeader } from "./run-header";
import { RunInputPanel } from "./run-input-panel";
import { StepDetail } from "./step-detail";
import { StepPager } from "./step-pager";
import { VerdictCard } from "./verdict-card";
import { VerdictHero } from "./verdict-hero";

type RunDiagnosisViewProps = { runId: string };

export function RunDiagnosisView({ runId }: RunDiagnosisViewProps) {
  const run = useGetRun(runId);
  const steps = useListSteps(runId);
  const [createdDiagnosisId, setCreatedDiagnosisId] = useState<string | null>(null);
  const [pickedStep, setPickedStep] = useState<number | null>(null);
  const [replayCheckId, setReplayCheckId] = useState<string | null>(null);

  const diagnosisId = createdDiagnosisId ?? run.data?.latest_diagnosis_id ?? null;
  const diagnosisQuery = useGetDiagnosis(diagnosisId);
  const diagnosis = diagnosisQuery.data;
  const isLive = isDiagnosisActive(diagnosis?.status);
  const checks = useListChecks(diagnosisId, { isLive: isLive || diagnosis === undefined });

  useEffect(() => {
    if (replayCheckId === null) return;
    document
      .getElementById("check-replays")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [replayCheckId]);

  if (isApiError(run.error, "not_found")) notFound();

  if (run.isError) {
    return (
      <QueryError error={run.error} what="this run" source="runs.load" onRetry={run.refetch} />
    );
  }
  if (!run.data) return <RunDiagnosisSkeleton />;

  const stepCount = steps.data?.length ?? run.data.step_count;
  const selectedStep = pickedStep ?? defaultSelectedStep(stepCount, diagnosis);
  const selected = steps.data?.find((step) => step.index === selectedStep);
  const dominoStep = steps.data?.find((step) => step.index === diagnosis?.first_domino_step);
  const replayCheck = checks.data?.find((check) => check.id === replayCheckId);
  const canDiagnose = run.data.status === "failed" && run.data.source === "recorded" && !isLive;

  function handleCreated(created: Diagnosis) {
    setCreatedDiagnosisId(created.id);
    setPickedStep(null);
    setReplayCheckId(null);
  }

  const stepStrip = steps.isError ? (
    <QueryError
      error={steps.error}
      what="the steps"
      source="runs.load_steps"
      onRetry={steps.refetch}
    />
  ) : (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
          Steps
        </h3>
        <span className="text-xs text-muted-foreground">
          Each step is a save point. Pick one to read it.
        </span>
      </div>
      <RunStepStrip
        stepCount={stepCount}
        diagnosis={diagnosis}
        selectedStep={selectedStep}
        onSelectStep={setPickedStep}
      />
    </div>
  );

  return (
    <div className="flex flex-col gap-6">
      <RunHeader
        run={run.data}
        title={diagnosis?.explanation?.title}
        actions={
          canDiagnose && (
            <DiagnoseRunButton
              runId={runId}
              hasDiagnosis={diagnosisId !== null}
              onCreated={handleCreated}
            />
          )
        }
      />

      {diagnosisId === null ? (
        <Panel>
          <EmptyState
            icon={SearchIcon}
            title="Not diagnosed yet"
            description={
              run.data.status === "failed"
                ? "Diagnose this run to replay it from its save points and find the first domino."
                : "Only failed recorded runs can be diagnosed."
            }
            action={
              canDiagnose && (
                <DiagnoseRunButton runId={runId} hasDiagnosis={false} onCreated={handleCreated} />
              )
            }
          />
          <div className="border-t px-5 py-5">{stepStrip}</div>
        </Panel>
      ) : diagnosisQuery.isError ? (
        <QueryError
          error={diagnosisQuery.error}
          what="the diagnosis"
          source="runs.load_diagnosis"
          onRetry={diagnosisQuery.refetch}
        />
      ) : diagnosis ? (
        <VerdictHero diagnosis={diagnosis}>{stepStrip}</VerdictHero>
      ) : (
        <Skeleton className="h-64 w-full rounded-xl" />
      )}

      {diagnosis?.status === "failed" && <DiagnosisFailed diagnosis={diagnosis} />}
      {diagnosis?.status === "done" && (
        <VerdictCard diagnosis={diagnosis} originalStep={dominoStep} />
      )}

      <div className="grid items-start gap-6 xl:grid-cols-2">
        <Panel
          id="selected-step"
          title={selectedStep === null ? "Step" : `Step ${selectedStep}`}
          description={
            selectedStep !== null && selectedStep === diagnosis?.first_domino_step
              ? "The first domino, as recorded."
              : "As recorded in the original run."
          }
          actions={
            selectedStep !== null && (
              <StepPager
                selectedStep={selectedStep}
                stepCount={stepCount}
                onSelectStep={setPickedStep}
              />
            )
          }
        >
          {selected ? (
            <StepDetail step={selected} />
          ) : steps.isPending ? (
            <div className="p-4">
              <Skeleton className="h-40 w-full" />
            </div>
          ) : (
            <p className="p-4 text-sm text-muted-foreground">Pick a step above to read it.</p>
          )}
        </Panel>
        <Panel
          id="checks"
          title="Checks"
          description="Each check keeps the first steps as recorded and replays the rest."
        >
          {diagnosisId === null ? (
            <p className="p-4 text-sm text-muted-foreground">
              Checks appear here once you diagnose the run.
            </p>
          ) : checks.isError ? (
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
              checks={checks.data}
              selectedCheckId={replayCheckId}
              onViewReplays={(check) => setReplayCheckId(check.id)}
            />
          ) : (
            <div className="p-4">
              <Skeleton className="h-40 w-full" />
            </div>
          )}
        </Panel>
      </div>
      {replayCheck && (
        <CheckReplays
          key={replayCheck.id}
          check={replayCheck}
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
      <div className="flex flex-col gap-3 border-b pb-6">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-8 w-96 max-w-full" />
      </div>
      <Skeleton className="h-64 w-full rounded-xl" />
      <div className="grid gap-6 xl:grid-cols-2">
        <Skeleton className="h-56 w-full rounded-xl" />
        <Skeleton className="h-56 w-full rounded-xl" />
      </div>
    </div>
  );
}
