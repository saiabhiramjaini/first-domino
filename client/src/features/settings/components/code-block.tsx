import { CopyButton } from "./copy-button";

type CodeBlockProps = { code: string; label: string };

export function CodeBlock({ code, label }: CodeBlockProps) {
  return (
    <div className="flex min-w-0 flex-col overflow-hidden rounded-md border bg-card">
      <div className="flex h-9 items-center justify-between gap-2 border-b pr-1.5 pl-3">
        <span className="font-mono text-xs text-muted-foreground">{label}</span>
        <CopyButton value={code} label={`Copy ${label}`} />
      </div>
      <pre className="overflow-x-auto p-3 font-mono text-xs leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}
