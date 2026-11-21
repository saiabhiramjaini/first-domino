import type { Message } from "@/api/generated";

type MessageViewProps = { message: Message };

function prettyArguments(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

export function MessageView({ message }: MessageViewProps) {
  const toolCalls = message.tool_calls ?? [];
  return (
    <div className="flex flex-col gap-3 text-sm">
      {message.content && <p className="text-pretty whitespace-pre-wrap">{message.content}</p>}
      {toolCalls.map((call) => (
        <div key={call.id} className="flex flex-col overflow-hidden rounded-md border bg-card">
          <span className="border-b px-3 py-1.5 font-mono text-xs">
            {call.name}
            <span className="text-muted-foreground">()</span>
          </span>
          <pre className="overflow-x-auto p-3 font-mono text-xs leading-relaxed">
            {prettyArguments(call.arguments)}
          </pre>
        </div>
      ))}
      {!message.content && toolCalls.length === 0 && (
        <p className="text-muted-foreground">This step has no text and no tool calls.</p>
      )}
    </div>
  );
}
