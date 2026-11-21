import { CopyButton } from "./copy-button";

type CodeBlockProps = { code: string; label: string };

export function CodeBlock({ code, label }: CodeBlockProps) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">{label}</span>
        <CopyButton value={code} label={`Copy ${label.toLowerCase()}`} />
      </div>
      <pre className="overflow-x-auto rounded-lg border bg-muted p-3 font-mono text-xs leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}
