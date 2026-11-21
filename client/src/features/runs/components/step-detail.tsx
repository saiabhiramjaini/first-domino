import type { Step } from "@/api/generated";
import { MessageView } from "@/components/runs/message-view";
import { prettyJson } from "@/components/runs/pretty-json";
import { formatInteger } from "@/lib/format";

type StepDetailProps = { step: Step; isDomino?: boolean };

// A step replayed with a fixed output never called the model, so it records no tokens.
export function isModelCall(step: Pick<Step, "tokens_in" | "tokens_out">): boolean {
  return step.tokens_in + step.tokens_out > 0;
}

export function StepDetail({ step, isDomino = false }: StepDetailProps) {
  const isFinalAnswer = (step.output.tool_calls ?? []).length === 0;
  return (
    <div className="flex flex-col">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b px-4 py-2.5">
        <span className="text-sm font-medium">
          Step {step.index}
          {isDomino && <span className="font-normal text-domino"> · first domino</span>}
        </span>
        <span className="font-mono text-xs text-muted-foreground">
          {isModelCall(step)
            ? `${step.model} · ${formatInteger(step.tokens_in)} in · ${formatInteger(step.tokens_out)} out · ${formatInteger(step.latency_ms)} ms`
            : "Output set by a replay"}
        </span>
      </div>
      <div className="flex flex-col gap-5 p-4">
        <section className="flex flex-col gap-2" aria-label="Model output">
          <h4 className="text-xs text-muted-foreground">Model output</h4>
          <MessageView message={step.output} />
        </section>
        {isFinalAnswer && (
          <p className="text-xs text-muted-foreground">
            No tool calls in this step: the model answered in text.
          </p>
        )}
        {step.tool_results.length > 0 && (
          <section className="flex flex-col gap-2" aria-label="Tool results">
            <h4 className="text-xs text-muted-foreground">Tool results</h4>
            {step.tool_results.map((result, position) => (
              <pre
                key={result.tool_call_id ?? `result-${position}`}
                className="overflow-x-auto rounded-md border bg-card p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap"
              >
                {result.content === null || result.content === undefined
                  ? "No content"
                  : prettyJson(result.content).text}
              </pre>
            ))}
          </section>
        )}
      </div>
    </div>
  );
}
