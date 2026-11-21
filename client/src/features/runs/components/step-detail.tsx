import type { Step } from "@/api/generated";
import { MessageView } from "@/components/runs/message-view";
import { formatInteger } from "@/lib/format";

type StepDetailProps = { step: Step };

export function StepDetail({ step }: StepDetailProps) {
  return (
    <div className="flex flex-col gap-4 rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium">Step {step.index}</h3>
        <span className="text-xs text-muted-foreground">
          {step.model} · {formatInteger(step.tokens_in)} in / {formatInteger(step.tokens_out)} out ·{" "}
          {formatInteger(step.latency_ms)} ms
        </span>
      </div>
      <MessageView message={step.output} />
      {step.tool_results.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium text-muted-foreground">Tool results</span>
          {step.tool_results.map((result, position) => (
            <pre
              key={result.tool_call_id ?? `result-${position}`}
              className="overflow-x-auto rounded-lg bg-muted p-3 font-mono text-xs whitespace-pre-wrap"
            >
              {result.content ?? "No content"}
            </pre>
          ))}
        </div>
      )}
    </div>
  );
}
