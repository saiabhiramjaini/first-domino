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
      {message.content && <p className="whitespace-pre-wrap">{message.content}</p>}
      {toolCalls.map((call) => (
        <div key={call.id} className="flex flex-col gap-1">
          <span className="font-mono text-xs text-muted-foreground">calls {call.name}</span>
          <pre className="overflow-x-auto rounded-lg bg-muted p-3 font-mono text-xs">
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
