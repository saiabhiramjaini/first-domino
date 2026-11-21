import { cn } from "@/lib/utils";

import { CopyButton } from "./copy-button";

type CodeBlockProps = { code: string; label: string; wrap?: boolean };

// `wrap` breaks long lines (a shell command) instead of scrolling them out of view.
export function CodeBlock({ code, label, wrap = false }: CodeBlockProps) {
  return (
    <div className="flex min-w-0 flex-col overflow-hidden rounded-md border bg-card">
      <div className="flex h-9 items-center justify-between gap-2 border-b pr-1.5 pl-3">
        <span className="font-mono text-xs text-muted-foreground">{label}</span>
        <CopyButton value={code} label={`Copy ${label}`} />
      </div>
      <pre
        className={cn(
          "p-3 font-mono text-xs leading-relaxed",
          wrap ? "break-all whitespace-pre-wrap" : "overflow-x-auto"
        )}
      >
        <code>{code}</code>
      </pre>
    </div>
  );
}
