"""record(): send each step of a run to First Domino without ever raising into the agent."""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from uuid import UUID

from first_domino._generated.models import (
    FinishRunRequest,
    Message,
    RecordStepRequest,
    RunOutcome,
    StartRunRequest,
    TaskInput,
)
from first_domino.client import FirstDominoClient, default_client

log = logging.getLogger("first_domino")


class RecordedRun:
    """Handle to one run being recorded. Every method is safe to call in any state.

    Without an API key, or after the API failed to start the run, every call is a no-op.
    """

    def __init__(
        self, client: FirstDominoClient, run_id: UUID | None, *, first_step: int = 1
    ) -> None:
        self._client = client
        self._run_id = run_id
        self._next_index = first_step
        self._finished = False
        self._flush_hooks: list[Callable[[], Awaitable[None]]] = []

    @property
    def run_id(self) -> UUID | None:
        """The run's id, or None when nothing is being recorded."""
        return self._run_id

    @property
    def finished(self) -> bool:
        """True once `finish` was called."""
        return self._finished

    def add_flush_hook(self, hook: Callable[[], Awaitable[None]]) -> None:
        """Run `hook` before the run finishes, such as `wrap` recording its last step."""
        self._flush_hooks.append(hook)

    async def step(
        self,
        *,
        model: str,
        output: Message,
        messages: Sequence[Message],
        tool_results: Sequence[Message] = (),
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: int = 0,
        index: int | None = None,
    ) -> None:
        """Record one step: a model turn, its tool results and the messages after it.

        `index` defaults to the step after the last one recorded.

        Example:
            >>> await run.step(model="gpt-x", output=reply, messages=history)
        """
        step_index = self._next_index if index is None else index
        self._next_index = step_index + 1
        run_id = self._run_id
        if run_id is None:
            return
        request = RecordStepRequest(
            run_id=run_id,
            index=step_index,
            model=model,
            output=output,
            tool_results=list(tool_results),
            messages=list(messages),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
        )
        await _quietly("record_step", lambda: self._client.record_step(request))

    async def finish(self, status: RunOutcome, final_output: str | None = None) -> None:
        """Finish the run as passed, failed or errored. Later calls do nothing.

        Example:
            >>> await run.finish(RunOutcome.failed, final_output="Added the visit on the wrong day")
        """
        if self._finished:
            return
        for hook in self._flush_hooks:
            await _quietly("flush", hook)
        self._finished = True
        run_id = self._run_id
        if run_id is None:
            return
        request = FinishRunRequest(run_id=run_id, status=status, final_output=final_output)
        await _quietly("finish_run", lambda: self._client.finish_run(request))


async def _quietly[T](action: str, call: Callable[[], Awaitable[T]]) -> T | None:
    """Run an API call and swallow any failure, so recording never breaks the agent."""
    try:
        return await call()
    except Exception:
        log.debug("first_domino.%s_failed", action, exc_info=True)
        return None


async def start_recording(
    agent_name: str, task_input: TaskInput, *, client: FirstDominoClient | None = None
) -> RecordedRun:
    """Start a recorded run and return its handle; a no-op handle when recording is off.

    Example:
        >>> run = await start_recording("call-assistant", fd.TaskInput(prompt="..."))
    """
    api = client or default_client()
    if not api.enabled:
        return RecordedRun(api, None)
    request = StartRunRequest(agent_name=agent_name, task_input=task_input)
    run = await _quietly("start_run", lambda: api.start_run(request))
    return RecordedRun(api, run.id if run else None)


@asynccontextmanager
async def record(
    agent_name: str, task_input: TaskInput, *, client: FirstDominoClient | None = None
) -> AsyncIterator[RecordedRun]:
    """Record one agent run. Dark without `FIRST_DOMINO_API_KEY`, and never raises.

    If the block raises before `run.finish`, the run is finished as `errored` and the
    exception continues unchanged.

    Example:
        >>> async with fd.record("call-assistant", fd.TaskInput(prompt=call_text)) as run:
        ...     await run.step(model=model, output=reply, messages=history)
        ...     await run.finish(fd.RunOutcome.passed, final_output=summary)
    """
    run = await start_recording(agent_name, task_input, client=client)
    try:
        yield run
    except BaseException:
        await run.finish(RunOutcome.errored)
        raise
