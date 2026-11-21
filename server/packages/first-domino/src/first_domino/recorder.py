"""record(): send each step of a run to First Domino without ever raising into the agent."""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Sequence
from contextlib import asynccontextmanager
from contextvars import ContextVar
from uuid import UUID

from first_domino._generated.models import (
    FailureReason,
    FinishRunRequest,
    Message,
    RecordStepRequest,
    RunOutcome,
    StartRunRequest,
    TaskInput,
)
from first_domino.client import MAX_REASON_CHARS, FirstDominoClient, default_client

log = logging.getLogger("first_domino")


class RecordedRun:
    """Handle to one run being recorded. Every method is safe to call in any state.

    A recorded run starts on the API at its first step or at `finish`, so tool names
    found before then (for example by `wrap`) are sent with it. Without an API key, or
    after the API failed to start the run, every call is a no-op.
    """

    def __init__(
        self,
        client: FirstDominoClient,
        run_id: UUID | None,
        *,
        first_step: int = 1,
        start: StartRunRequest | None = None,
    ) -> None:
        self._client = client
        self._run_id = run_id
        self._start = start
        self._next_index = first_step
        self._finished = False
        self._flush_hooks: list[Callable[[], Awaitable[None]]] = []

    @property
    def run_id(self) -> UUID | None:
        """The run's id once started, or None when nothing is being recorded."""
        return self._run_id

    @property
    def recording(self) -> bool:
        """True while steps can still be sent: started, or waiting to start."""
        return self._run_id is not None or self._start is not None

    def add_tool_names(self, names: Iterable[str]) -> None:
        """Add the names of tools the agent was given, before the run starts.

        Example:
            >>> run.add_tool_names(["lookup_contact", "end_call"])
        """
        if self._start is None:
            return
        known = list(self._start.tool_names or [])
        known += [name for name in names if name not in known]
        self._start = self._start.model_copy(update={"tool_names": known})

    async def start(self) -> None:
        """Start the run on the API now, so it shows as running before its first step.

        Example:
            >>> await run.start()
        """
        await self._started()

    async def _started(self) -> UUID | None:
        start, self._start = self._start, None
        if start is not None:
            run = await _quietly("start_run", lambda: self._client.start_run(start))
            self._run_id = run.id if run else None
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
        run_id = await self._started()
        if run_id is None:
            return
        request = RecordStepRequest(
            run_id=run_id,
            index=step_index,
            model=model or "unknown",
            output=_listed(output),
            tool_results=[_listed(m) for m in tool_results],
            messages=[_listed(m) for m in messages],
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
        )
        await _quietly("record_step", lambda: self._client.record_step(request))

    async def finish(
        self,
        status: RunOutcome,
        final_output: str | None = None,
        *,
        failure_reason: str | None = None,
    ) -> None:
        """Finish the run as passed, failed or errored. Later calls do nothing.

        `failure_reason` says in words why a `failed` run failed; the diagnosis uses it.
        It is cut to 2000 characters and dropped for any other status.

        Example:
            >>> await run.finish(
            ...     RunOutcome.failed,
            ...     final_output="Added the visit on Tuesday",
            ...     failure_reason="The caller asked for Thursday",
            ... )
        """
        if self._finished:
            return
        for hook in self._flush_hooks:
            await _quietly("flush", hook)
        self._finished = True
        run_id = await self._started()
        if run_id is None:
            return
        request = FinishRunRequest(
            run_id=run_id,
            status=status,
            final_output=final_output,
            failure_reason=_failure_reason(status, failure_reason),
        )
        await _quietly("finish_run", lambda: self._client.finish_run(request))


def _failure_reason(status: RunOutcome, reason: str | None) -> FailureReason | None:
    if status != RunOutcome.failed or not reason:
        return None
    return FailureReason(reason[:MAX_REASON_CHARS])


def _listed(message: Message) -> Message:
    """The API wants `tool_calls` as a list, never null."""
    if message.tool_calls is None:
        return message.model_copy(update={"tool_calls": []})
    return message


async def _quietly[T](action: str, call: Callable[[], Awaitable[T]]) -> T | None:
    """Run an API call and swallow any failure, so recording never breaks the agent."""
    try:
        return await call()
    except Exception:
        log.debug("first_domino.%s_failed", action, exc_info=True)
        return None


_RECORDING: ContextVar[RecordedRun | None] = ContextVar("first_domino_recording", default=None)


def current_recording() -> RecordedRun | None:
    """The run of the enclosing `record` block, if any."""
    return _RECORDING.get()


def start_recording(
    agent_name: str,
    task_input: TaskInput,
    *,
    tool_names: Sequence[str] = (),
    client: FirstDominoClient | None = None,
) -> RecordedRun:
    """Return the handle of a new recorded run; a no-op handle when recording is off.

    Example:
        >>> run = fd.start_recording("call-assistant", fd.TaskInput(prompt="..."))
    """
    api = client or default_client()
    if not api.enabled:
        return RecordedRun(api, None)
    start = StartRunRequest(
        agent_name=agent_name, task_input=task_input, tool_names=list(tool_names)
    )
    return RecordedRun(api, None, start=start)


@asynccontextmanager
async def record(
    agent_name: str,
    task_input: TaskInput,
    *,
    tool_names: Sequence[str] = (),
    client: FirstDominoClient | None = None,
) -> AsyncIterator[RecordedRun]:
    """Record one agent run. Dark without `FIRST_DOMINO_API_KEY`, and never raises.

    If the block raises before `run.finish`, the run is finished as `errored` and the
    exception continues unchanged.

    `tool_names` lists the tools the agent was given; `wrap` also fills it from `tools=`.

    Example:
        >>> async with fd.record("call-assistant", fd.TaskInput(prompt=call_text)) as run:
        ...     await run.step(model=model, output=reply, messages=history)
        ...     await run.finish(fd.RunOutcome.passed, final_output=summary)
    """
    run = start_recording(agent_name, task_input, tool_names=tool_names, client=client)
    token = _RECORDING.set(run)
    try:
        yield run
    except BaseException:
        await run.finish(RunOutcome.errored)
        raise
    finally:
        _RECORDING.reset(token)
