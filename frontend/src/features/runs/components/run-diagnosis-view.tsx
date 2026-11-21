"use client";

import { notFound } from "next/navigation";
import { useState } from "react";

import type { Diagnosis } from "@/api/generated";
import { EmptyState } from "@/components/feedback/empty-state";
import { QueryError } from "@/components/feedback/query-error";
import { RunStepStrip } from "@/components/runs/run-step-strip";
import { defaultSelectedStep } from "@/components/runs/step-strip-state";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { isDiagnosisActive } from "@/hooks/api/diagnosis-activity";
import { useGetDiagnosis } from "@/hooks/api/use-get-diagnosis";
import { useGetRun } from "@/hooks/api/use-get-run";
import { useListChecks } from "@/hooks/api/use-list-checks";
import { useListSteps } from "@/hooks/api/use-list-steps";
import { isApiError } from "@/lib/api-error";

import { CheckList } from "./check-list";
import { DiagnoseRunButton } from "./diagnose-run-button";
import { DiagnosisFailed } from "./diagnosis-failed";
import { DiagnosisProgress } from "./diagnosis-progress";
import { RunHeader } from "./run-header";
import { StepDetail } from "./step-detail";
import { StepPager } from "./step-pager";
import { VerdictCard } from "./verdict-card";

type RunDiagnosisViewProps = { runId: string };

export function RunDiagnosisView({ runId }: RunDiagnosisViewProps) {
  const run = useGetRun(runId);
  const steps = useListSteps(runId);
  const [createdDiagnosisId, setCreatedDiagnosisId] = useState<string | null>(null);
  const [pickedStep, setPickedStep] = useState<number | null>(null);

  const diagnosisId = createdDiagnosisId ?? run.data?.latest_diagnosis_id ?? null;
  const diagnosisQuery = useGetDiagnosis(diagnosisId);
  const diagnosis = diagnosisQuery.data;
  const isLive = isDiagnosisActive(diagnosis?.status);
  const checks = useListChecks(diagnosisId, { isLive: isLive || diagnosis === undefined });

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
  const canDiagnose = run.data.status === "failed" && run.data.source === "recorded" && !isLive;

  function handleCreated(created: Diagnosis) {
    setCreatedDiagnosisId(created.id);
    setPickedStep(null);
  }

  return (
    <div className="flex flex-col gap-6">
      <RunHeader
        run={run.data}
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

      <Card>
        <CardHeader>
          <CardTitle>Diagnosis</CardTitle>
          <CardDescription>
            Each check keeps the first steps exactly as recorded and replays the rest. The first
            step from which every replay fails is the first domino.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          {diagnosisId === null ? (
            <EmptyState
              title="Not diagnosed yet"
              description={
                run.data.status === "failed"
                  ? "Diagnose this run to replay it from its save points and find the first domino."
                  : "Only failed recorded runs can be diagnosed."
              }
            />
          ) : diagnosisQuery.isError ? (
            <QueryError
              error={diagnosisQuery.error}
              what="the diagnosis"
              source="runs.load_diagnosis"
              onRetry={diagnosisQuery.refetch}
            />
          ) : diagnosis ? (
            <DiagnosisProgress diagnosis={diagnosis} />
          ) : (
            <Skeleton className="h-6 w-64" />
          )}

          {steps.isError ? (
            <QueryError
              error={steps.error}
              what="the steps"
              source="runs.load_steps"
              onRetry={steps.refetch}
            />
          ) : (
            <RunStepStrip
              stepCount={stepCount}
              diagnosis={diagnosis}
              selectedStep={selectedStep}
              onSelectStep={setPickedStep}
            />
          )}
        </CardContent>
      </Card>

      {diagnosis?.status === "done" && (
        <VerdictCard diagnosis={diagnosis} originalStep={dominoStep} />
      )}
      {diagnosis?.status === "failed" && <DiagnosisFailed diagnosis={diagnosis} />}

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="flex flex-col gap-3" aria-labelledby="step-title">
          <div className="flex items-center justify-between gap-2">
            <h2 id="step-title" className="font-medium">
              Selected step
            </h2>
            {selectedStep !== null && (
              <StepPager
                selectedStep={selectedStep}
                stepCount={stepCount}
                onSelectStep={setPickedStep}
              />
            )}
          </div>
          {selected ? (
            <StepDetail step={selected} />
          ) : steps.isPending ? (
            <Skeleton className="h-40 w-full" />
          ) : (
            <p className="text-sm text-muted-foreground">Pick a step above to read it.</p>
          )}
        </section>
        <section className="flex flex-col gap-3" aria-labelledby="checks-title">
          <h2 id="checks-title" className="font-medium">
            Checks
          </h2>
          {diagnosisId === null ? (
            <p className="text-sm text-muted-foreground">
              Checks appear here once you diagnose the run.
            </p>
          ) : checks.isError ? (
            <QueryError
              error={checks.error}
              what="the checks"
              source="runs.load_checks"
              onRetry={checks.refetch}
            />
          ) : checks.data ? (
            <CheckList checks={checks.data} />
          ) : (
            <Skeleton className="h-40 w-full" />
          )}
        </section>
      </div>
    </div>
  );
}

function RunDiagnosisSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-20 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  );
}
