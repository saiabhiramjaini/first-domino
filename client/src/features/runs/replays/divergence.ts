import type { Message, Step } from "@/api/generated";

function normalizeArguments(raw: string): string {
  try {
    return JSON.stringify(sortKeys(JSON.parse(raw)));
  } catch {
    return raw.trim();
  }
}

function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, inner]) => [key, sortKeys(inner)])
    );
  }
  return value;
}

export function messageSignature(message: Message): string {
  const calls = (message.tool_calls ?? []).map(
    (call) => `${call.name}(${normalizeArguments(call.arguments)})`
  );
  return JSON.stringify([message.content?.trim() ?? null, calls]);
}

export function stepsByIndex(steps: Step[]): Map<number, Step> {
  return new Map(steps.map((step) => [step.index, step]));
}

/**
 * The first step after the save point where the replay does something different from the
 * original run: a different output, or one run has a step the other does not.
 */
export function divergenceStep(original: Step[], replay: Step[], savePoint: number): number | null {
  const originalByIndex = stepsByIndex(original);
  const replayByIndex = stepsByIndex(replay);
  const last = Math.max(savePoint, ...original.map((s) => s.index), ...replay.map((s) => s.index));
  for (let index = savePoint + 1; index <= last; index += 1) {
    const before = originalByIndex.get(index);
    const after = replayByIndex.get(index);
    if (!before || !after) return index;
    if (messageSignature(before.output) !== messageSignature(after.output)) return index;
  }
  return null;
}

export function comparedStepIndices(lanes: Step[][], savePoint: number): number[] {
  const last = Math.max(savePoint, ...lanes.flat().map((step) => step.index));
  return Array.from({ length: last - savePoint }, (_, offset) => savePoint + offset + 1);
}
