import type { Step } from "@/api/generated";

const MAX_ARGUMENTS = 3;
const MAX_VALUE_LENGTH = 40;

function shortValue(value: unknown): string {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > MAX_VALUE_LENGTH ? `${text.slice(0, MAX_VALUE_LENGTH)}…` : text;
}

function argumentPairs(raw: string): string[] {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) return [raw];
    const pairs = Object.entries(parsed).map(([key, value]) => `${key}: ${shortValue(value)}`);
    return pairs.length > MAX_ARGUMENTS
      ? [...pairs.slice(0, MAX_ARGUMENTS), `+${pairs.length - MAX_ARGUMENTS} more`]
      : pairs;
  } catch {
    return [shortValue(raw)];
  }
}

type StepCellProps = { step: Step | undefined };

export function StepCell({ step }: StepCellProps) {
  if (!step) return <span className="text-xs text-muted-foreground">No step: the run ended</span>;
  const calls = step.output.tool_calls ?? [];
  return (
    <div className="flex flex-col gap-1.5 text-xs">
      {step.output.content && <p className="line-clamp-3">{step.output.content}</p>}
      {calls.map((call) => (
        <div key={call.id} className="flex flex-col gap-0.5">
          <span className="font-mono font-medium">{call.name}</span>
          {argumentPairs(call.arguments).map((pair) => (
            <span key={pair} className="font-mono break-all text-muted-foreground">
              {pair}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}
