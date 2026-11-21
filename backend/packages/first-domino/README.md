# first-domino

Find the step where a failed AI agent run became doomed, and prove it.

First Domino records each step of your agent's runs. When a run fails, it replays the run from its own save points to find the first step after which the run always fails (the first domino), then fixes that one step and replays again to prove it. Replays run on your side, in a worker next to your agent, so your code, tools and secrets never leave your machines.

## Install

```bash
pip install "first-domino[openai] @ git+<repo-url>#subdirectory=backend/packages/first-domino"
```

Python 3.12 or newer. The SDK depends on `httpx`, `pydantic` and `pydantic-settings`; the `openai` extra is only needed for `fd.wrap`.

## Configure

| Variable | Meaning | Default |
| --- | --- | --- |
| `FIRST_DOMINO_API_KEY` | Your project API key (`fd_live_...`). Without it, recording does nothing. | none |
| `FIRST_DOMINO_BASE_URL` | The First Domino API. | `http://localhost:8000` |
| `FIRST_DOMINO_WORKER_CONCURRENCY` | Replays one worker runs at once. | `4` |

Variables can also live in a `.env` file in the working directory.

## Record runs

The SDK is async. Recording never raises into your agent: if First Domino is down, your agent behaves exactly as without it.

```python
import first_domino as fd

task = fd.TaskInput(prompt=call_transcript, metadata={"task_id": "t01"})
async with fd.record("call-assistant", task) as run:
    # Either wrap your OpenAI client: each completion becomes a step.
    client = fd.wrap(AsyncOpenAI(), run)
    ...
    # Or record steps yourself, one per model turn plus its tool results.
    await run.step(model=model, output=reply, tool_results=results, messages=history)

    passed = my_success_check(...)
    await run.finish(fd.RunOutcome.passed if passed else fd.RunOutcome.failed)
```

Put whatever your success check needs (such as a task id) in `TaskInput.metadata`; the worker gets it back on every replay. A failed run is diagnosed automatically.

`fd.message_from_openai` and `fd.messages_to_openai` convert between OpenAI chat message params and First Domino messages.

## Run the replay worker

The worker only calls out: it leases replay jobs, runs your agent from the save point it is given, runs your success check, and reports the outcome.

```python
worker = fd.Worker(agent_names=["call-assistant"])


@worker.agent("call-assistant")
async def replay(ctx: fd.ReplayContext) -> CallResult:
    # Continue from ctx.messages. If ctx.replacement_output is set, use it as the next
    # step's output instead of calling the model. If ctx.model_override is set, run the
    # rest with that model. Record each step with ctx.run.step(...).
    ...


@worker.success_check("call-assistant")
def check(task_input: fd.TaskInput, result: CallResult) -> bool:
    return my_success_check(task_input.metadata["task_id"], result)


await worker.run()  # loops forever
```

One failed job never stops the worker: a crash in your agent or check is reported as `errored` and the worker moves on. It refuses to start without an API key or without both handlers for each agent name.

## Diagnose from code

```python
diagnosis = await fd.diagnose(run_id)
async with asyncio.timeout(600):
    final = await fd.wait_for_diagnosis(diagnosis.id)
print(final.first_domino_step, final.explanation)
```

## Test without a server

`first_domino.testing` has an in-memory API, so you can test your worker with no network:

```python
from first_domino.testing import FakeApi, fake_client, make_job

api = FakeApi()
api.jobs.append(make_job(agent_name="call-assistant", from_step=2))
worker = fd.Worker(agent_names=["call-assistant"], client=fake_client(api))
...
assert await worker.run_once() == fd.ReplayOutcome.passed
```

## Modules

| Module | Job |
| --- | --- |
| `recorder` | `record()` and `RecordedRun`: send each step without ever raising into the agent. |
| `wrap` | `wrap()`: record every completion made through an async OpenAI client. |
| `worker` | `Worker` and `ReplayContext`: lease, replay, check, submit. |
| `diagnose` | `diagnose()` and `wait_for_diagnosis()`. |
| `openai_format` | Convert between OpenAI message params and First Domino messages. |
| `client` | Typed async HTTP client for the API. |
| `settings` | `SdkSettings`, read with the `FIRST_DOMINO_` prefix. |
| `errors` | `ConfigurationError` and `ApiRequestError`. |
| `testing` | An in-memory API for tests. |
| `_generated/` | Wire models generated from `../api/openapi.json` by `make sdk-models`. Do not edit. |
