import type { Run } from "@/api/generated";
import { Panel } from "@/components/layout/panel";
import { prettyJson } from "@/components/runs/pretty-json";
import { cn } from "@/lib/utils";

type RunInputPanelProps = { run: Run };

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}

// What the agent was asked, what it could use, and what it returned.
export function RunInputPanel({ run }: RunInputPanelProps) {
  const output = run.final_output ? prettyJson(run.final_output) : null;
  return (
    <Panel title="Task">
      <div className="flex flex-col gap-5 p-4 text-sm">
        <Field label="Input">
          <p className="text-pretty whitespace-pre-wrap">{run.task_input.prompt}</p>
        </Field>
        {run.tool_names.length > 0 && (
          <Field label="Tools">
            <ul className="flex flex-wrap gap-1.5" aria-label="Tools the agent was given">
              {run.tool_names.map((name) => (
                <li
                  key={name}
                  className="rounded border px-1.5 py-0.5 font-mono text-xs text-muted-foreground"
                >
                  {name}
                </li>
              ))}
            </ul>
          </Field>
        )}
        {output && (
          <Field label="Final output">
            <pre
              className={cn(
                "overflow-x-auto rounded-md border bg-card p-3 whitespace-pre-wrap",
                output.isJson ? "font-mono text-xs leading-relaxed" : "font-sans text-sm"
              )}
            >
              {output.text}
            </pre>
          </Field>
        )}
      </div>
    </Panel>
  );
}
