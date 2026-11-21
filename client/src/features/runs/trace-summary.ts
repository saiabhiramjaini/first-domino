import type { Message } from "@/api/generated";

const MAX_SUMMARY = 110;

function clip(text: string): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > MAX_SUMMARY ? `${flat.slice(0, MAX_SUMMARY - 1)}…` : flat;
}

function argumentsText(raw: string): string {
  try {
    const parsed: unknown = JSON.parse(raw || "{}");
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) return raw;
    return Object.entries(parsed)
      .map(
        ([key, value]) =>
          `${key}=${typeof value === "string" ? `"${value}"` : JSON.stringify(value)}`
      )
      .join(", ");
  } catch {
    return raw;
  }
}

/** One line for a step in the trace: its first tool call, or else what it said. */
export function stepSummary(output: Message): string {
  const [call, ...more] = output.tool_calls ?? [];
  if (call) {
    const extra = more.length > 0 ? ` +${more.length} more` : "";
    return clip(`${call.name}(${argumentsText(call.arguments)})${extra}`);
  }
  if (output.content) return clip(output.content);
  return "No text and no tool calls";
}
