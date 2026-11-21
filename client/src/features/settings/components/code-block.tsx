import { CopyButton } from "./copy-button";

type CodeBlockProps = { code: string; label: string; step?: number };

export function CodeBlock({ code, label, step }: CodeBlockProps) {
  return (
    <div className="flex flex-col overflow-hidden rounded-lg border bg-background/60">
      <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
        <span className="flex items-center gap-2 text-sm font-medium">
          {step !== undefined && (
            <span className="flex size-5 items-center justify-center rounded-full bg-domino/15 font-mono text-[11px] text-domino">
              {step}
            </span>
          )}
          {label}
        </span>
        <CopyButton value={code} label={`Copy ${label.toLowerCase()}`} />
      </div>
      <pre className="overflow-x-auto p-3 font-mono text-xs leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}
