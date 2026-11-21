import type { Step } from "@/api/generated";
import { MessageView } from "@/components/runs/message-view";
import { formatInteger } from "@/lib/format";

type StepDetailProps = { step: Step };

// A step replayed with a fixed output never called the model, so it records no tokens.
export function isModelCall(step: Pick<Step, "tokens_in" | "tokens_out">): boolean {
  return step.tokens_in + step.tokens_out > 0;
}

export function StepDetail({ step }: StepDetailProps) {
  return (
    <div className="flex flex-col gap-4 p-4">
      <p className="font-mono text-[11px] text-muted-foreground">
        {isModelCall(step)
          ? `${step.model} · ${formatInteger(step.tokens_in)} in / ${formatInteger(step.tokens_out)} out · ${formatInteger(step.latency_ms)} ms`
          : "Output set by replay"}
      </p>
      <MessageView message={step.output} />
      {step.tool_results.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
            Tool results
          </span>
          {step.tool_results.map((result, position) => (
            <pre
              key={result.tool_call_id ?? `result-${position}`}
              className="overflow-x-auto rounded-lg border bg-background/60 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap"
            >
              {result.content ?? "No content"}
            </pre>
          ))}
        </div>
      )}
    </div>
  );
}
