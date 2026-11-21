"""wrap(): record every chat completion made through an async OpenAI client as a step."""

import inspect
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Any, cast

from first_domino._generated.models import Message, MessageRole
from first_domino.openai_format import message_from_openai
from first_domino.recorder import RecordedRun

log = logging.getLogger("first_domino")


@dataclass(frozen=True, slots=True)
class _PendingStep:
    model: str
    before: list[Message]
    output: Message
    tokens_in: int
    tokens_out: int
    latency_ms: int


class _StepTracker:
    """Turns successive completions into steps.

    A step is a model turn plus the results of the tools it called, and those results
    only appear in the next request's messages. So each completion is held until the
    next request (or the run's finish) shows its tool results, then recorded.
    """

    def __init__(self, run: RecordedRun) -> None:
        self._run = run
        self._pending: _PendingStep | None = None
        run.add_flush_hook(self.flush)

    def note_tools(self, tools: Sequence[Mapping[str, Any]]) -> None:
        """Pass the function tool names of a request to the run, before it starts."""
        try:
            names = [t["function"]["name"] for t in tools if t.get("type") == "function"]
            self._run.add_tool_names(names)
        except Exception:
            log.debug("first_domino.wrap_tools_failed", exc_info=True)

    async def observe(self, request: Mapping[str, Any], response: Any, latency_ms: int) -> None:
        messages = [message_from_openai(m) for m in request.get("messages", [])]
        await self._record_pending(messages)
        usage = getattr(response, "usage", None)
        self._pending = _PendingStep(
            model=str(request.get("model", "")),
            before=messages,
            output=message_from_openai(response.choices[0].message.model_dump()),
            tokens_in=getattr(usage, "prompt_tokens", 0) or 0,
            tokens_out=getattr(usage, "completion_tokens", 0) or 0,
            latency_ms=latency_ms,
        )

    async def flush(self) -> None:
        """Record the last completion with no tool results."""
        await self._record_pending(None)

    async def _record_pending(self, next_messages: Sequence[Message] | None) -> None:
        pending, self._pending = self._pending, None
        if pending is None:
            return
        after = list(next_messages or [])[len(pending.before) + 1 :]
        tool_results = [m for m in after if m.role == MessageRole.tool]
        await self._run.step(
            model=pending.model,
            output=pending.output,
            tool_results=tool_results,
            messages=[*pending.before, pending.output, *tool_results],
            tokens_in=pending.tokens_in,
            tokens_out=pending.tokens_out,
            latency_ms=pending.latency_ms,
        )


class _Completions:
    def __init__(self, inner: Any, tracker: _StepTracker) -> None:
        self._inner = inner
        self._tracker = tracker

    async def create(self, **kwargs: Any) -> Any:
        self._tracker.note_tools(kwargs.get("tools") or [])
        started = perf_counter()
        response = await self._inner.create(**kwargs)
        latency_ms = round((perf_counter() - started) * 1000)
        try:
            await self._tracker.observe(kwargs, response, latency_ms)
        except Exception:
            log.debug("first_domino.wrap_observe_failed", exc_info=True)
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _Chat:
    def __init__(self, inner: Any, tracker: _StepTracker) -> None:
        self._inner = inner
        self.completions = _Completions(inner.completions, tracker)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _Client:
    def __init__(self, inner: Any, tracker: _StepTracker) -> None:
        self._inner = inner
        self.chat = _Chat(inner.chat, tracker)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def wrap[ClientT](client: ClientT, run: RecordedRun) -> ClientT:
    """Record every `chat.completions.create` call through an async OpenAI client.

    Each completion becomes a step once its tool results show up in the next request,
    and the last one is recorded when the run finishes. The function names in `tools=`
    become the run's `tool_names`. Returns `client` unchanged when recording is off or
    the client is not async.

    Example:
        >>> async with fd.record("call-assistant", task) as run:
        ...     client = fd.wrap(AsyncOpenAI(), run)
        ...     await client.chat.completions.create(model=model, messages=messages)
    """
    create = getattr(getattr(getattr(client, "chat", None), "completions", None), "create", None)
    if not run.recording or not inspect.iscoroutinefunction(create):
        return client
    return cast(ClientT, _Client(client, _StepTracker(run)))
