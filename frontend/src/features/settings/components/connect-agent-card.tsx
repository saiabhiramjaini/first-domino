import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { CodeBlock } from "./code-block";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ENVIRONMENT_SNIPPET = `pip install first-domino

export FIRST_DOMINO_API_KEY=fd_live_...   # a key from the list above
export FIRST_DOMINO_BASE_URL=${API_URL}`;

const RECORD_SNIPPET = `import first_domino as fd
from openai import OpenAI

task = fd.TaskInput(prompt="Handle the incoming call from the dentist's office", metadata={"task_id": "t1"})

with fd.record(agent_name="call-assistant", task_input=task) as run:
    client = fd.wrap(OpenAI(), run)   # every chat completion becomes a step
    result = run_agent(client, task)
    run.finish(status="passed" if result.ok else "failed", final_output=result.text)`;

const WORKER_SNIPPET = `worker = fd.Worker(agent_names=["call-assistant"])

@worker.agent("call-assistant")
def replay(ctx: fd.ReplayContext):
    # ctx carries the saved messages, the fixed step to use, and the replay run
    return run_agent_from(ctx)

@worker.success_check("call-assistant")
def check(task_input: fd.TaskInput, result) -> bool:
    return result.ok

worker.run()   # polls for replay jobs; only connects outward`;

export function ConnectAgentCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Connect your agent</CardTitle>
        <CardDescription>
          Record runs with the SDK, then run a replay worker next to your agent. Failed runs are
          diagnosed automatically.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <CodeBlock label="1. Install and configure" code={ENVIRONMENT_SNIPPET} />
        <CodeBlock label="2. Record a run" code={RECORD_SNIPPET} />
        <CodeBlock label="3. Run the replay worker" code={WORKER_SNIPPET} />
      </CardContent>
    </Card>
  );
}
