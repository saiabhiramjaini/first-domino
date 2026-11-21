import type { Run } from "@/api/generated";
import { Panel } from "@/components/layout/panel";

type RunInputPanelProps = { run: Run };

// What the agent was asked, what it could use, and what it answered.
export function RunInputPanel({ run }: RunInputPanelProps) {
  return (
    <Panel title="Task" description="The input this run was recorded with.">
      <div className="flex flex-col gap-5 p-4 text-sm">
        <p className="whitespace-pre-wrap text-pretty">{run.task_input.prompt}</p>
        {run.tool_names.length > 0 && (
          <div className="flex flex-col gap-2">
            <span className="text-xs font-medium text-muted-foreground">Tools</span>
            <ul className="flex flex-wrap gap-1.5" aria-label="Tools the agent was given">
              {run.tool_names.map((name) => (
                <li
                  key={name}
                  className="rounded-md border bg-muted/40 px-1.5 py-0.5 font-mono text-xs text-muted-foreground"
                >
                  {name}
                </li>
              ))}
            </ul>
          </div>
        )}
        {run.final_output && (
          <div className="flex flex-col gap-2">
            <span className="text-xs font-medium text-muted-foreground">Final output</span>
            <p className="rounded-lg border bg-background/60 p-3 whitespace-pre-wrap">
              {run.final_output}
            </p>
          </div>
        )}
      </div>
    </Panel>
  );
}
