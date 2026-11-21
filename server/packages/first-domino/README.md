# first-domino

Find the step where a failed AI agent run went wrong, and prove it.

First Domino records every run of your agent, live. When a run fails, it replays the run from its own save points to find the first step after which the run always fails (the first domino), then rewrites that one step and replays again to prove the fix. Replays run in a worker on your side, so your code, tools and secrets never leave your machines.

Works with any agent that calls a model through the OpenAI or Anthropic SDK, or a framework built on them: LangChain, the OpenAI Agents SDK, LlamaIndex, CrewAI, or a plain loop. Sync or async, streaming or not, and any OpenAI-compatible API.

## Install

```bash
pip install first-domino
```

Python 3.12+. Set the key from your project's Settings page:

```bash
export FIRST_DOMINO_API_KEY=fd_live_...
```

Without a key the SDK does nothing, so the same code runs in tests and in production.

## 1. Record your agent: two lines

Mark the function that runs your agent. Each call becomes one run, and every model call inside it becomes a step, as it happens.

```python
import first_domino as fd

@fd.entrypoint("support-bot", check=lambda question, answer: "refund" in answer)
def answer(question: str) -> str:
    ...  # your agent, unchanged
```

- `check(output)` or `check(input, output)` says whether the run passed. A run that raises is recorded as `errored`, and your exception continues.
- Already know the answer inside your code? Call `fd.set_outcome(passed=False, reason="...")`; it wins over `check`.
- The function's arguments are saved with the run so it can be replayed. Use JSON-friendly types: text, numbers, lists, dicts, dataclasses or pydantic models.
- Recording never raises into your agent. If First Domino is unreachable, your code behaves exactly as without it.
- Failed runs are diagnosed on their own.

### Tools with side effects

During a replay, the steps before the one being tested come from the recording. Mark a tool that must not run twice (sends an email, moves money) so it returns its recorded result there instead:

```python
@fd.tool
def send_refund(order_id: str, amount: float) -> str:
    ...
```

Put it under your framework's own decorator (`@function_tool`, `@tool`). Read-only tools need no marking.

## 2. Start the replay worker

Run this next to your agent, with the same code and keys:

```python
import first_domino as fd
import my_agent  # the module with your @fd.entrypoint

fd.serve()
```

The worker only connects outward. When First Domino needs a replay, the worker calls your function again: model calls up to the save point are answered from the recording, the next one with the fixed step when there is one, and the rest by the model. Your `check` decides whether the replay passed.

Async code can run `await fd.worker().run()` instead.

## Advanced

The two lines above cover most agents. These lower-level APIs remain for full control.

### Record runs by hand

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
                result = run_tool(call)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
        outcome = fd.RunOutcome.passed if call_handled(task_id) else fd.RunOutcome.failed
        await run.finish(outcome, final_output=reply.content)
```

- Recording never raises into your agent. If First Domino is unreachable, your code behaves exactly as without it.
- If the block raises, the run is finished as `errored` and your exception continues.
- Put what your success check needs (here `task_id`) in `TaskInput.metadata`. Replays get it back.
- A run finished as `failed` is diagnosed automatically.
- Not using OpenAI's client directly? Call `await run.step(model=..., output=..., tool_results=..., messages=...)` once per model turn. `fd.message_from_openai` converts OpenAI message dicts.

### Agents built with the OpenAI Agents SDK

Install `first-domino[agents]` and run the agent through the adapter. Every model turn is recorded as a step, and a replay resumes `Runner.run` from the save point:

```python
from first_domino import openai_agents as fd_agents

async with fd.record("call-assistant", task) as run:
    result = await fd_agents.run_recorded(agent, call_text, run)
    await run.finish(fd.RunOutcome.passed if handled(result) else fd.RunOutcome.failed)


@worker.agent("call-assistant")
async def replay(ctx: fd.ReplayContext) -> RunResult:
    return await fd_agents.replay(ctx, agent)  # replacement output and model override included
```

Replays resume from the recorded messages; your tools only see new calls, so restore any state they need for the save point first. Streamed turns (`Runner.run_streamed`) are not recorded.

### Write the replay worker by hand

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

## Diagnose from code

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
| `FIRST_DOMINO_BASE_URL` | The First Domino API. Point it at your own server if you self-host. | `https://api-first-domino.abhiramtech.in` |
| `FIRST_DOMINO_WORKER_CONCURRENCY` | Replays one worker runs at once. | `4` |
| `FIRST_DOMINO_LEASE_WAIT_SECONDS` | How long one lease call waits for a job (0 to 20). | `10` |
| `FIRST_DOMINO_TIMEOUT_SECONDS` | Timeout of one API call. | `30` |

Settings can also live in a `.env` file in the working directory.

| Module | Job |
| --- | --- |
| `instrument` | `entrypoint()`, `tool()`, `set_outcome()`, `serve()`, `worker()` and `init()`: the two-line integration. |
| `capture` | Records model calls at the HTTP layer (`httpx` and `httpx2`) and answers them during a replay. |
| `providers` | The OpenAI Chat Completions, OpenAI Responses and Anthropic Messages wire formats. |
| `recorder` | `record()`, `start_recording()` and `RecordedRun`: send each step without ever raising into the agent. |
| `wrap` | `wrap()`: record every completion made through an async OpenAI client. |
| `worker` | `Worker` and `ReplayContext`: lease, replay, check, submit. |
| `diagnose` | `diagnose()` and `wait_for_diagnosis()`. |
| `openai_format` | Convert between OpenAI message params and First Domino messages. |
| `openai_agents` | Record and replay OpenAI Agents SDK agents (`first-domino[agents]`). |
| `responses_format` | Convert between Responses input items and First Domino messages. |
| `client` | `FirstDominoClient`, the typed async HTTP client. |
| `settings` | `SdkSettings`, read with the `FIRST_DOMINO_` prefix. |
| `errors` | `ConfigurationError` and `ApiRequestError` (with the API's stable `code`). |
| `testing` | An in-memory API for tests. |
| `_generated/` | Wire models generated from `api/openapi.json` by `make sdk-models`. Do not edit. |
