"""Record model calls where every agent makes them: the HTTP request to the model API.

`install()` patches `send` on the `httpx` and `httpx2` clients, which the OpenAI and
Anthropic SDKs (and the frameworks built on them, such as LangChain, LlamaIndex, CrewAI
and the OpenAI Agents SDK) use for every request. Outside a recorded session the patch
passes every request straight through. Inside one, a POST to a model API is recorded as
a step, or, during a replay, answered from the recording.

Recording never breaks the agent: any failure inside First Domino is logged at debug
level and the request goes through as if First Domino were not installed.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import importlib
import json
import logging
import threading
from collections.abc import AsyncIterator, Callable, Coroutine, Iterator, Mapping, Sequence
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import timedelta
from time import perf_counter
from types import ModuleType
from typing import Any

from first_domino._generated.models import (
    Message,
    MessageRole,
    ReplayDrift,
    RunOutcome,
    Step,
    ToolName,
)
from first_domino.errors import ReplayStopped
from first_domino.providers import ModelReply, Provider, provider_for
from first_domino.recorder import RecordedRun

log = logging.getLogger("first_domino")

_THREAD_NAME = "first-domino"


class Background:
    """One daemon thread running an event loop for the SDK's own API calls.

    Recording happens here so it works the same for sync and async agents, and never
    blocks or shares connections with the agent's own event loop.
    """

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def loop(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            if self._loop is None:
                loop = asyncio.new_event_loop()
                threading.Thread(target=loop.run_forever, name=_THREAD_NAME, daemon=True).start()
                self._loop = loop
            return self._loop

    def submit[T](self, coro: Coroutine[Any, Any, T]) -> concurrent.futures.Future[T]:
        return asyncio.run_coroutine_threadsafe(coro, self.loop())


BACKGROUND = Background()


@dataclass(frozen=True, slots=True)
class KeptToolResult:
    """A tool result of a kept step, as the recording has it."""

    step: int
    tool_call_id: str
    tool_name: str | None
    content: str | None


@dataclass(frozen=True, slots=True)
class ReplayPlan:
    """How a replay answers model calls and `@fd.tool` calls.

    Model calls 1..`from_step` get the recorded outputs, call `from_step + 1` gets
    `replacement` when set, and every later call goes to the model (as `model_override`
    when set). `@fd.tool` functions return the recorded results while the replay is
    still inside the recorded part. `kept_results` (by tool call id) is what the agent
    must send back for the replay to still match the recording.
    """

    from_step: int
    outputs: Mapping[int, Message]
    tool_results: Mapping[str, Sequence[str | None]]
    kept_results: Mapping[str, KeptToolResult]
    replacement: Message | None = None
    model_override: str | None = None

    @classmethod
    def of(
        cls,
        steps: Sequence[Step],
        from_step: int,
        replacement: Message | None,
        model_override: str | None,
    ) -> ReplayPlan:
        kept = [step for step in steps if step.index <= from_step]
        results: dict[str, list[str | None]] = {}
        kept_results: dict[str, KeptToolResult] = {}
        for step in sorted(kept, key=lambda s: s.index):
            names = {call.id: call.name for call in step.output.tool_calls or []}
            for result in step.tool_results:
                name = names.get(result.tool_call_id or "")
                if name is not None:
                    results.setdefault(name, []).append(result.content)
                if result.tool_call_id is not None:
                    kept_results[result.tool_call_id] = KeptToolResult(
                        step.index, result.tool_call_id, name, result.content
                    )
        return cls(
            from_step=from_step,
            outputs={step.index: step.output for step in kept},
            tool_results=results,
            kept_results=kept_results,
            replacement=replacement,
            model_override=model_override,
        )


@dataclass(slots=True)
class _Pending:
    index: int
    model: str
    before: list[Message]
    output: Message
    tokens_in: int
    tokens_out: int
    latency_ms: int


@dataclass(slots=True)
class Verdict:
    """What the agent code said about its own run with `fd.set_outcome`."""

    passed: bool
    reason: str | None = None


class Session:
    """One run being recorded (or replayed): numbers model calls and turns them into steps.

    A step is a model call plus the results of the tools it asked for. Those results only
    show up in a later request, so a step that called tools is held until a request
    carries their results, or until the run ends.
    """

    def __init__(
        self,
        run: RecordedRun,
        *,
        replay: ReplayPlan | None = None,
        stop: threading.Event | None = None,
        background: Background = BACKGROUND,
    ) -> None:
        self.run = run
        self.replay = replay
        self.stop = stop
        self.verdict: Verdict | None = None
        self.drift: ReplayDrift | None = None
        self._background = background
        self._lock = threading.Lock()
        self._calls = 0
        self._retry: list[int] = []
        self._pending: list[_Pending] = []
        self._tools_used: dict[str, int] = {}
        self._started = replay is not None
        self._tail: concurrent.futures.Future[None] | None = None

    # --- model calls -------------------------------------------------------------------

    def reserve(self) -> int:
        """Number the next model call. A failed call gives its number back with `release`."""
        with self._lock:
            if self._retry:
                return self._retry.pop(0)
            self._calls += 1
            return self._calls

    def release(self, index: int) -> None:
        with self._lock:
            self._retry.append(index)
            self._retry.sort()

    def served(self, index: int) -> Message | None:
        """The recorded (or fixed) output a replay answers call `index` with, if any."""
        plan = self.replay
        if plan is None:
            return None
        if index <= plan.from_step:
            return plan.outputs.get(index)
        if index == plan.from_step + 1:
            return plan.replacement
        return None

    def model_override(self, index: int) -> str | None:
        plan = self.replay
        return plan.model_override if plan is not None and index > plan.from_step else None

    def is_recorded(self, index: int) -> bool:
        """False for calls a replay answers from the recording: they are not new steps."""
        return self.replay is None or index > self.replay.from_step

    def saw_request(self, messages: Sequence[Message], tool_names: Sequence[str]) -> None:
        """Note a request: its tools, and the tool results that complete earlier steps."""
        self.run.add_tool_names(tool_names)
        self._start()
        results = {m.tool_call_id: m for m in messages if m.role == MessageRole.tool}
        with self._lock:
            done = [p for p in self._pending if _answered(p, results)]
            self._pending = [p for p in self._pending if p not in done]
        for pending in done:
            self._record(
                pending, [results[c.id] for c in pending.output.tool_calls or [] if c.id in results]
            )

    def check_replay(self, index: int, messages: Sequence[Message]) -> None:
        """Note the first kept step whose tool results the replay sends back changed.

        Only requests up to `from_step + 1` are compared: by then every kept result was
        due, and later requests may legitimately trim or rewrite old history.
        """
        plan = self.replay
        if plan is None or self.drift is not None or index > plan.from_step + 1:
            return
        drift = _drift_in(plan, index, messages)
        if drift is not None:
            with self._lock:
                self.drift = self.drift or drift

    @property
    def stopping(self) -> bool:
        """True once a replay is not worth going on: its job ended, or it drifted."""
        return self.drift is not None or (self.stop is not None and self.stop.is_set())

    def finished_call(
        self, index: int, before: list[Message], reply: ModelReply, latency_ms: int
    ) -> None:
        """A model call answered: record it now, or hold it until its tool results show up."""
        if not self.is_recorded(index):
            return
        pending = _Pending(
            index, reply.model, before, reply.message, reply.tokens_in, reply.tokens_out, latency_ms
        )
        if reply.message.tool_calls:
            with self._lock:
                self._pending.append(pending)
        else:
            self._record(pending, [])

    # --- tools -------------------------------------------------------------------------

    def recorded_tool_result(self, name: str) -> tuple[bool, str | None]:
        """During the recorded part of a replay, the next recorded result of tool `name`."""
        plan = self.replay
        if plan is None:
            return False, None
        with self._lock:
            if self._calls > plan.from_step:
                return False, None
            used = self._tools_used.get(name, 0)
            results = plan.tool_results.get(name, ())
            if used >= len(results):
                return False, None
            self._tools_used[name] = used + 1
            return True, results[used]

    # --- sending -----------------------------------------------------------------------

    def close(
        self, outcome: RunOutcome | None, final_output: str | None
    ) -> concurrent.futures.Future[None]:
        """Record what is still held, then finish the run (unless `outcome` is None)."""
        with self._lock:
            pending, self._pending = self._pending, []
        for step in sorted(pending, key=lambda p: p.index):
            self._record(step, [])
        if outcome is not None:
            self._submit(lambda: self.run.finish(outcome, final_output))
        return self._submit(_nothing)

    def _start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
        self._submit(self.run.start)

    def _record(self, pending: _Pending, tool_results: list[Message]) -> None:
        async def send() -> None:
            await self.run.step(
                index=pending.index,
                model=pending.model,
                output=pending.output,
                tool_results=tool_results,
                messages=[*pending.before, pending.output, *tool_results],
                tokens_in=pending.tokens_in,
                tokens_out=pending.tokens_out,
                latency_ms=pending.latency_ms,
            )

        self._submit(send)

    def _submit(
        self, call: Callable[[], Coroutine[Any, Any, None]]
    ) -> concurrent.futures.Future[None]:
        """Send API calls one after another, in the order they were made."""
        with self._lock:
            previous = self._tail
            self._tail = self._background.submit(_after(previous, call))
            return self._tail


def _answered(pending: _Pending, results: Mapping[str | None, Message]) -> bool:
    return any(call.id in results for call in pending.output.tool_calls or [])


def _drift_in(plan: ReplayPlan, index: int, messages: Sequence[Message]) -> ReplayDrift | None:
    """The earliest kept step whose result in this request (call `index`) differs, or is
    missing while other results of the same step `index - 1` are there.

    A request with none of step `index - 1`'s results is not checked for missing ones: a
    side model call (a guardrail, a sub-agent) may come between a step and its results.
    """
    sent = {
        m.tool_call_id: m.content
        for m in messages
        if m.role == MessageRole.tool and m.tool_call_id is not None
    }
    previous = [kept for kept in plan.kept_results.values() if kept.step == index - 1]
    partial = any(kept.tool_call_id in sent for kept in previous)
    changed = [
        kept
        for kept in plan.kept_results.values()
        if (kept.tool_call_id in sent and not _same_content(kept.content, sent[kept.tool_call_id]))
        or (partial and kept.step == index - 1 and kept.tool_call_id not in sent)
    ]
    if not changed:
        return None
    first = min(changed, key=lambda kept: kept.step)
    name = ToolName(first.tool_name) if first.tool_name is not None else None
    return ReplayDrift(step=first.step, tool_name=name)


def _same_content(recorded: str | None, replayed: str | None) -> bool:
    """Identical text, or JSON with equal values (key order and whitespace do not count)."""
    if recorded == replayed:
        return True
    if recorded is None or replayed is None:
        return False
    try:
        return json.loads(recorded) == json.loads(replayed)
    except ValueError:
        return False


async def _nothing() -> None:
    return None


async def _after(
    previous: concurrent.futures.Future[None] | None, call: Callable[[], Coroutine[Any, Any, None]]
) -> None:
    if previous is not None:
        try:
            await asyncio.wrap_future(previous)
        except Exception:
            log.debug("first_domino.send_failed", exc_info=True)
    try:
        await call()
    except Exception:
        log.debug("first_domino.send_failed", exc_info=True)


SESSION: ContextVar[Session | None] = ContextVar("first_domino_session", default=None)
_ACTIVE: set[Session] = set()
_ACTIVE_LOCK = threading.Lock()


def activate(session: Session) -> None:
    with _ACTIVE_LOCK:
        _ACTIVE.add(session)


def deactivate(session: Session) -> None:
    with _ACTIVE_LOCK:
        _ACTIVE.discard(session)


def current_session() -> Session | None:
    """The session of the running entrypoint.

    Threads started without copying the context (some frameworks run tools that way)
    do not see the context variable; when exactly one run is active, it is that one.
    """
    session = SESSION.get()
    if session is not None:
        return session
    with _ACTIVE_LOCK:
        return next(iter(_ACTIVE)) if len(_ACTIVE) == 1 else None


# --- HTTP ---------------------------------------------------------------------------------


@dataclass(slots=True)
class _Call:
    """One model request inside a session."""

    session: Session
    provider: Provider
    module: ModuleType
    request: Any
    body: dict[str, Any]
    index: int
    before: list[Message]
    started: float = field(default_factory=perf_counter)
    done: bool = False

    @property
    def streaming(self) -> bool:
        return bool(self.body.get("stream"))

    def served_response(self) -> Any | None:
        """A response built from the recording, when the replay answers this call."""
        message = self.session.served(self.index)
        if message is None:
            return None
        model = str(self.body.get("model", ""))
        if self.streaming:
            content = self.provider.build_stream(message, model)
            headers = {"content-type": "text/event-stream"}
        else:
            content = json.dumps(self.provider.build_response(message, model)).encode()
            headers = {"content-type": "application/json"}
        response = self.module.Response(200, headers=headers, content=content, request=self.request)
        response.elapsed = timedelta(0)
        reply = ModelReply(message, model)
        self.session.finished_call(self.index, self.before, reply, 0)
        return response

    def outgoing(self) -> Any:
        """The request to send: the original, or with the replay's model swapped in."""
        model = self.session.model_override(self.index)
        if model is None:
            return self.request
        body = {**self.body, "model": model}
        headers = {k: v for k, v in self.request.headers.items() if k.lower() != "content-length"}
        swapped = self.module.Request(
            self.request.method,
            self.request.url,
            headers=headers,
            content=json.dumps(body).encode(),
        )
        swapped.extensions = self.request.extensions
        return swapped

    def failed(self) -> None:
        self.session.release(self.index)

    def received(self, response: Any) -> Any:
        """Look at the model's answer; return the response the agent should get."""
        if response.status_code >= 400:
            self.failed()
            return response
        events = "text/event-stream" in response.headers.get("content-type", "")
        if hasattr(response, "_content"):
            self._finish(response.content, stream=events)
            return response
        async_ = isinstance(response.stream, self.module.AsyncByteStream)
        tee = _tee_class(self.module, async_=async_)

        def done(raw: bytes) -> None:
            self._finish(_decoded(self.module, response, raw), stream=events)

        response.stream = tee(response.stream, done)
        return response

    def _finish(self, content: bytes, *, stream: bool) -> None:
        if self.done:
            return
        self.done = True
        latency_ms = round((perf_counter() - self.started) * 1000)
        try:
            if stream:
                reply = self.provider.parse_stream(content)
            else:
                reply = self.provider.parse_response(json.loads(content))
        except Exception:
            log.debug("first_domino.parse_failed provider=%s", self.provider.name, exc_info=True)
            return
        if not reply.model:
            reply = ModelReply(
                reply.message, str(self.body.get("model", "")), reply.tokens_in, reply.tokens_out
            )
        self.session.finished_call(self.index, self.before, reply, latency_ms)


def _decoded(module: ModuleType, response: Any, raw: bytes) -> bytes:
    encoding = response.headers.get("content-encoding")
    if not encoding or encoding == "identity":
        return raw
    return module.Response(200, headers={"content-encoding": encoding}, content=raw).content


class _Tee:
    """Passes a response body through and hands the whole of it over at the end."""

    def __init__(self, inner: Any, done: Callable[[bytes], None]) -> None:
        self._inner = inner
        self._done = done
        self._chunks: list[bytes] = []
        self._finished = False

    def _finish(self) -> None:
        if not self._finished:
            self._finished = True
            try:
                self._done(b"".join(self._chunks))
            except Exception:
                log.debug("first_domino.stream_failed", exc_info=True)


class _SyncTee(_Tee):
    def __iter__(self) -> Iterator[bytes]:
        for chunk in self._inner:
            self._chunks.append(chunk)
            yield chunk
        self._finish()

    def close(self) -> None:
        self._finish()
        self._inner.close()


class _AsyncTee(_Tee):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self._inner:
            self._chunks.append(chunk)
            yield chunk
        self._finish()

    async def aclose(self) -> None:
        self._finish()
        await self._inner.aclose()


_TEES: dict[tuple[str, bool], type] = {}


def _tee_class(module: ModuleType, *, async_: bool) -> type:
    """The tee as a byte stream of `module`, which its `Response` checks for."""
    key = (module.__name__, async_)
    if key not in _TEES:
        bases = (_AsyncTee, module.AsyncByteStream) if async_ else (_SyncTee, module.SyncByteStream)
        _TEES[key] = type(f"FirstDomino{bases[1].__name__}", bases, {})
    return _TEES[key]


def _begin(module: ModuleType, request: Any) -> _Call | None:
    """A `_Call` when this request is a model call inside a session, else None."""
    if request.method != "POST" or threading.current_thread().name == _THREAD_NAME:
        return None
    provider = provider_for(request.url.path)
    if provider is None:
        return None
    session = current_session()
    if session is None:
        return None
    try:
        body = json.loads(request.content)
    except Exception:
        return None
    if not isinstance(body, dict):
        return None
    before = provider.request_messages(body)
    session.saw_request(before, provider.tool_names(body))
    index = session.reserve()
    _safely("drift", lambda: session.check_replay(index, before), None)
    return _Call(session, provider, module, request, body, index, before)


def _stop_if_asked(call: _Call) -> None:
    """Ends a replay at its next model call once nobody needs its result, or once it
    drifted from the recording (it is no evidence then, so it spends no more model calls).

    Only model calls stop: the worker's own API calls must go on, even when they find this
    session as the only active one.
    """
    if call.session.stopping:
        call.failed()
        raise ReplayStopped


def _safely[T](action: str, call: Callable[[], T], fallback: T) -> T:
    try:
        return call()
    except Exception:
        log.debug("first_domino.%s_failed", action, exc_info=True)
        return fallback


def _patch(module: ModuleType) -> None:
    client, async_client = module.Client, module.AsyncClient
    if getattr(client.send, "__first_domino__", False):
        return
    sync_send, async_send = client.send, async_client.send

    def send(self: Any, request: Any, **kwargs: Any) -> Any:
        call = _safely("capture", lambda: _begin(module, request), None)
        if call is None:
            return sync_send(self, request, **kwargs)
        _stop_if_asked(call)
        served = _safely("serve", call.served_response, None)
        if served is not None:
            return served
        try:
            response = sync_send(self, _safely("swap", call.outgoing, request), **kwargs)
        except BaseException:
            call.failed()
            raise
        return _safely("receive", lambda: call.received(response), response)

    async def asend(self: Any, request: Any, **kwargs: Any) -> Any:
        call = _safely("capture", lambda: _begin(module, request), None)
        if call is None:
            return await async_send(self, request, **kwargs)
        _stop_if_asked(call)
        served = _safely("serve", call.served_response, None)
        if served is not None:
            return served
        try:
            response = await async_send(self, _safely("swap", call.outgoing, request), **kwargs)
        except BaseException:
            call.failed()
            raise
        return _safely("receive", lambda: call.received(response), response)

    send.__first_domino__ = True  # type: ignore[attr-defined]
    asend.__first_domino__ = True  # type: ignore[attr-defined]
    send.__wrapped__ = sync_send  # type: ignore[attr-defined]
    asend.__wrapped__ = async_send  # type: ignore[attr-defined]
    client.send = send
    async_client.send = asend


_INSTALL_LOCK = threading.Lock()


def install() -> None:
    """Patch the HTTP clients model SDKs use. Safe to call many times."""
    with _INSTALL_LOCK:
        for name in ("httpx", "httpx2"):
            try:
                module = importlib.import_module(name)
            except ImportError:
                continue
            _safely("install", lambda module=module: _patch(module), None)
