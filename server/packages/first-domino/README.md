# first-domino

Find the step where a failed AI agent run became doomed, and prove it.

First Domino records every step of your agent's runs. When a run fails, it replays the run from its own save points to find the first step after which the run always fails (the first domino), then rewrites that one step and replays again to prove the fix. Replays run in a worker on your side, so your code, tools and secrets never leave your machines.

## 1. Install

```bash
pip install "first-domino[openai] @ git+<repo-url>#subdirectory=server/packages/first-domino"
```

Python 3.12+. Depends on `httpx`, `pydantic` and `pydantic-settings`; the `openai` extra is only for `fd.wrap`.

```bash
export FIRST_DOMINO_API_KEY=fd_live_...                # from Settings > API keys
export FIRST_DOMINO_BASE_URL=https://api.example.com   # default http://localhost:8000
```

Without an API key the SDK does nothing, so the same code runs in tests and in production.

## 2. Record runs

Wrap your OpenAI client inside `fd.record`. Each completion becomes a step (the model turn plus the tool results it led to), and the tools you pass become the run's tool list. This is a complete call assistant loop:

```python
import first_domino as fd
from openai import AsyncOpenAI

openai = AsyncOpenAI()


async def answer_call(call_text: str, task_id: str) -> None:
    task = fd.TaskInput(prompt=call_text, metadata={"task_id": task_id})
    async with fd.record("call-assistant", task) as run:
        client = fd.wrap(openai, run)
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": call_text}]
        while True:
            response = await client.chat.completions.create(
                model=MODEL, messages=messages, tools=TOOLS
            )
            reply = response.choices[0].message
            messages.append(reply.model_dump(exclude_none=True))
            if not reply.tool_calls:
                break
            for call in reply.tool_calls:
                messages.append({"role": "tool", "tool_call_id": call.id, "content": run_tool(call)})
        outcome = fd.RunOutcome.passed if call_handled(task_id) else fd.RunOutcome.failed
        await run.finish(outcome, final_output=reply.content)
```

- Recording never raises into your agent. If First Domino is unreachable, your code behaves exactly as without it.
- If the block raises, the run is finished as `errored` and your exception continues.
- Put what your success check needs (here `task_id`) in `TaskInput.metadata`. Replays get it back.
- A run finished as `failed` is diagnosed automatically.
- Not using OpenAI's client directly? Call `await run.step(model=..., output=..., tool_results=..., messages=...)` once per model turn. `fd.message_from_openai` converts OpenAI message dicts.

## 3. Run the replay worker

The worker only calls out. It leases replay jobs, runs your agent from the save point it is given, runs your success check, and reports the outcome.

```python
worker = fd.Worker(agent_names=["call-assistant"])


@worker.agent("call-assistant")
async def replay(ctx: fd.ReplayContext) -> str:
    # Continue from ctx.messages (from_step steps already done). When ctx.replacement_output
    # is set, use it as the next model turn instead of calling the model. When
    # ctx.model_override is set, use that model. Record each step with ctx.run.step(...).
    task_id = ctx.task_input.metadata["task_id"]
    await continue_call(fd.messages_to_openai(ctx.messages), ctx)
    return task_id


@worker.success_check("call-assistant")
def check(task_input: fd.TaskInput, task_id: str) -> bool:
    return call_handled(task_id)


await worker.run()  # leases forever, several jobs at a time
```

- One failed job never stops the worker: a crash in your agent or check is reported as `errored` and the loop goes on.
- The worker refuses to start without an API key or without both handlers for each agent name.
- `FIRST_DOMINO_WORKER_CONCURRENCY` (default 4) sets how many replays run at once.

## 4. Diagnose from code

Failed runs are diagnosed automatically. To start one yourself and wait for the verdict:

```python
diagnosis = await fd.diagnose(run_id)
async with asyncio.timeout(600):
    final = await fd.wait_for_diagnosis(diagnosis.id)
print(final.verdict_kind, final.first_domino_step, final.explanation.title)
# step_verified 6 Converted AM appointment to PM
```

## Test without a server

`first_domino.testing` is an in-memory API, so you can test your worker with no network:

```python
from first_domino.testing import FakeApi, fake_client, make_job

api = FakeApi()
api.jobs.append(make_job(agent_name="call-assistant", from_step=2))
worker = fd.Worker(agent_names=["call-assistant"], client=fake_client(api))
# register @worker.agent and @worker.success_check as above
assert await worker.run_once() == fd.ReplayOutcome.passed
```

## Reference

| Setting | Meaning | Default |
| --- | --- | --- |
| `FIRST_DOMINO_API_KEY` | Project API key. Without it, recording does nothing. | none |
| `FIRST_DOMINO_BASE_URL` | The First Domino API. | `http://localhost:8000` |
| `FIRST_DOMINO_WORKER_CONCURRENCY` | Replays one worker runs at once. | `4` |
| `FIRST_DOMINO_LEASE_WAIT_SECONDS` | How long one lease call waits for a job (0 to 20). | `10` |
| `FIRST_DOMINO_TIMEOUT_SECONDS` | Timeout of one API call. | `30` |

Settings can also live in a `.env` file in the working directory.

| Module | Job |
| --- | --- |
| `recorder` | `record()`, `start_recording()` and `RecordedRun`: send each step without ever raising into the agent. |
| `wrap` | `wrap()`: record every completion made through an async OpenAI client. |
| `worker` | `Worker` and `ReplayContext`: lease, replay, check, submit. |
| `diagnose` | `diagnose()` and `wait_for_diagnosis()`. |
| `openai_format` | Convert between OpenAI message params and First Domino messages. |
| `client` | `FirstDominoClient`, the typed async HTTP client. |
| `settings` | `SdkSettings`, read with the `FIRST_DOMINO_` prefix. |
| `errors` | `ConfigurationError` and `ApiRequestError` (with the API's stable `code`). |
| `testing` | An in-memory API for tests. |
| `_generated/` | Wire models generated from `api/openapi.json` by `make sdk-models`. Do not edit. |
