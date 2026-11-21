"""The two-line integration: `@fd.entrypoint` on the function that runs the agent, then
`fd.serve()` to let First Domino replay it.

Works with any agent that calls a model over HTTP through the OpenAI or Anthropic SDKs,
or a framework built on them (LangChain, LlamaIndex, CrewAI, the OpenAI Agents SDK, a
plain loop), sync or async, streaming or not.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import logging
import typing
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, cast, overload

from pydantic import TypeAdapter

from first_domino import capture
from first_domino._generated.models import RunOutcome, StartRunRequest, TaskInput
from first_domino.client import FirstDominoClient, default_client
from first_domino.recorder import RecordedRun
from first_domino.settings import SdkSettings
from first_domino.worker import ReplayContext, Worker

log = logging.getLogger("first_domino")

INPUT_KEY = "fd_input"
_MAX_TEXT = 8000

type Check = Callable[..., bool | Awaitable[bool]]


class _Config:
    """The client the recorder uses, built on first use from the environment or `init`."""

    def __init__(self) -> None:
        self.client: FirstDominoClient | None = None
        self.settings: SdkSettings | None = None

    def recorder_client(self) -> FirstDominoClient:
        if self.client is None:
            settings = self.settings or default_client().settings
            self.client = FirstDominoClient(settings)
        return self.client


_CONFIG = _Config()


def init(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    client: FirstDominoClient | None = None,
) -> None:
    """Turn on recording of model calls. Optional: `@fd.entrypoint` calls it for you.

    Reads `FIRST_DOMINO_API_KEY` and `FIRST_DOMINO_BASE_URL` unless given here. Without
    an API key nothing is recorded and the agent runs exactly as before.

    Example:
        >>> import first_domino as fd
        >>> fd.init()
    """
    if client is not None:
        _CONFIG.client = client
    elif api_key is not None or base_url is not None:
        changes: dict[str, Any] = {}
        if api_key is not None:
            changes["api_key"] = api_key
        if base_url is not None:
            changes["base_url"] = base_url
        _CONFIG.settings = SdkSettings(**changes)
        _CONFIG.client = None
    capture.install()


def set_outcome(*, passed: bool, reason: str | None = None) -> None:
    """Say whether the current run passed, from inside the agent code.

    Use it when your own code already knows (a failed validation, an eval you run in
    line). It wins over the entrypoint's `check`. Does nothing outside a run.

    Example:
        >>> fd.set_outcome(passed=False, reason="Booked the wrong day")
    """
    session = capture.current_session()
    if session is not None:
        session.verdict = capture.Verdict(passed, reason)


@overload
def tool[F: Callable[..., Any]](fn: F, *, name: str | None = None) -> F: ...
@overload
def tool[F: Callable[..., Any]](
    fn: None = None, *, name: str | None = None
) -> Callable[[F], F]: ...
def tool(fn: Any = None, *, name: str | None = None) -> Any:
    """Mark a tool that must not run again when First Domino replays a run.

    During a replay, the steps before the one being tested are taken from the recording.
    A marked tool returns its recorded result there instead of running, so a tool that
    sends an email or charges a card does not do it twice. After that point it runs
    normally. Read-only tools need no marking. Put it under your framework's decorator.

    Example:
        >>> @function_tool
        ... @fd.tool
        ... def send_email(to: str, body: str) -> str: ...
    """

    def decorate[F: Callable[..., Any]](fn: F) -> F:
        tool_name = name or fn.__name__
        returns = _return_type(fn)

        def recorded() -> tuple[bool, Any]:
            session = capture.current_session()
            if session is None:
                return False, None
            found, content = session.recorded_tool_result(tool_name)
            return (True, _as_type(content, returns)) if found else (False, None)

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def run_async(*args: Any, **kwargs: Any) -> Any:
                found, result = recorded()
                return result if found else await fn(*args, **kwargs)

            return cast(F, run_async)

        @functools.wraps(fn)
        def run(*args: Any, **kwargs: Any) -> Any:
            found, result = recorded()
            return result if found else fn(*args, **kwargs)

        return cast(F, run)

    return decorate(fn) if fn is not None else decorate


@dataclass(slots=True)
class Entrypoint:
    """A function registered with `@fd.entrypoint`: how to record, check and replay it."""

    name: str
    fn: Callable[..., Any]
    check: Check | None
    prompt: Callable[..., str] | None
    metadata: Callable[..., Mapping[str, str]] | None

    @property
    def is_async(self) -> bool:
        return inspect.iscoroutinefunction(self.fn)

    def task_input(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> TaskInput:
        """What the run was asked: a readable prompt, plus the arguments to replay it."""
        bound = inspect.signature(self.fn).bind(*args, **kwargs)
        bound.apply_defaults()
        hints = _hints(self.fn)
        values = {
            key: TypeAdapter(hints.get(key, Any)).dump_python(value, mode="json")
            for key, value in bound.arguments.items()
        }
        metadata = dict(self.metadata(*args, **kwargs)) if self.metadata else {}
        metadata[INPUT_KEY] = json.dumps(values)
        return TaskInput(prompt=self._prompt(args, kwargs, values), metadata=metadata)

    def _prompt(self, args: tuple[Any, ...], kwargs: dict[str, Any], values: dict[str, Any]) -> str:
        if self.prompt is not None:
            return self.prompt(*args, **kwargs)
        texts = [v for v in (*args, *kwargs.values()) if isinstance(v, str)]
        if len(values) == 1 and texts:
            return texts[0][:_MAX_TEXT]
        return json.dumps(values)[:_MAX_TEXT]

    def arguments(self, task_input: TaskInput) -> dict[str, Any]:
        """The recorded arguments, rebuilt as the function's parameter types."""
        stored = (task_input.metadata or {}).get(INPUT_KEY)
        if stored is None:
            msg = f"run of {self.name} has no recorded arguments to replay"
            raise ValueError(msg)
        hints = _hints(self.fn)
        values: dict[str, Any] = json.loads(stored)
        return {
            key: TypeAdapter(hints.get(key, Any)).validate_python(v) for key, v in values.items()
        }

    async def passed(
        self, session: capture.Session, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any
    ) -> bool:
        """`fd.set_outcome` if the code called it, else the check, else passed."""
        if session.verdict is not None:
            return session.verdict.passed
        if self.check is None:
            return True
        params = [
            p
            for p in inspect.signature(self.check).parameters.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        if len(params) >= 2:
            bound = inspect.signature(self.fn).bind(*args, **kwargs)
            bound.apply_defaults()
            given = bound.arguments
            verdict = self.check(
                next(iter(given.values())) if len(given) == 1 else dict(given), result
            )
        else:
            verdict = self.check(result)
        return bool(await verdict) if inspect.isawaitable(verdict) else bool(verdict)


REGISTRY: dict[str, Entrypoint] = {}


@overload
def entrypoint[F: Callable[..., Any]](name: F) -> F: ...
@overload
def entrypoint[F: Callable[..., Any]](
    name: str | None = None,
    *,
    check: Check | None = None,
    prompt: Callable[..., str] | None = None,
    metadata: Callable[..., Mapping[str, str]] | None = None,
) -> Callable[[F], F]: ...
def entrypoint(
    name: Any = None,
    *,
    check: Check | None = None,
    prompt: Callable[..., str] | None = None,
    metadata: Callable[..., Mapping[str, str]] | None = None,
) -> Any:
    """Record every run of the function that runs your agent, live, step by step.

    Each call becomes one run in First Domino. Every model call made inside it (through
    the OpenAI or Anthropic SDK, or any framework built on them) becomes a step, as it
    happens. `check(output)` or `check(input, output)` says whether the run passed; a
    run that raises is recorded as errored.

    The arguments are saved with the run (they must be JSON-friendly: text, numbers,
    lists, dicts, dataclasses or pydantic models), so `fd.serve()` can call the
    function again to replay it.

    Example:
        >>> @fd.entrypoint("support-bot", check=lambda question, answer: "refund" in answer)
        ... def answer(question: str) -> str:
        ...     return client.chat.completions.create(...).choices[0].message.content
    """
    if callable(name):
        return entrypoint()(name)

    def decorate[F: Callable[..., Any]](fn: F) -> F:
        entry = Entrypoint(name or fn.__name__, fn, check, prompt, metadata)
        REGISTRY[entry.name] = entry
        if entry.is_async:

            @functools.wraps(fn)
            async def run_async(*args: Any, **kwargs: Any) -> Any:
                return await _run_async(entry, args, kwargs)

            return cast(F, run_async)

        @functools.wraps(fn)
        def run(*args: Any, **kwargs: Any) -> Any:
            return _run_sync(entry, args, kwargs)

        return cast(F, run)

    return decorate


def _open(
    entry: Entrypoint, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> capture.Session | None:
    """A new recorded session, or None when recording is off or a run is already open."""
    try:
        capture.install()
        if capture.SESSION.get() is not None:
            return None
        client = _CONFIG.recorder_client()
        if not client.enabled:
            return None
        start = StartRunRequest(agent_name=entry.name, task_input=entry.task_input(args, kwargs))
        return capture.Session(RecordedRun(client, None, start=start))
    except Exception:
        log.debug("first_domino.entrypoint_failed", exc_info=True)
        return None


def _final_output(result: Any) -> str | None:
    if result is None:
        return None
    if isinstance(result, str):
        return result[:_MAX_TEXT]
    try:
        return json.dumps(TypeAdapter(Any).dump_python(result, mode="json"))[:_MAX_TEXT]
    except Exception:
        return repr(result)[:_MAX_TEXT]


def _outcome(*, passed: bool) -> RunOutcome:
    return RunOutcome.passed if passed else RunOutcome.failed


async def _run_async(entry: Entrypoint, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    session = _open(entry, args, kwargs)
    if session is None:
        return await entry.fn(*args, **kwargs)
    token = capture.SESSION.set(session)
    capture.activate(session)
    try:
        result = await entry.fn(*args, **kwargs)
    except BaseException:
        _close(session, token)
        await _wait(session.close(RunOutcome.errored, None))
        raise
    _close(session, token)
    try:
        passed = await entry.passed(session, args, kwargs, result)
    except Exception:
        log.warning("first_domino.check_failed agent=%s", entry.name, exc_info=True)
        await _wait(session.close(RunOutcome.errored, _final_output(result)))
        return result
    await _wait(session.close(_outcome(passed=passed), _final_output(result)))
    return result


def _run_sync(entry: Entrypoint, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    session = _open(entry, args, kwargs)
    if session is None:
        return entry.fn(*args, **kwargs)
    token = capture.SESSION.set(session)
    capture.activate(session)
    try:
        result = entry.fn(*args, **kwargs)
    except BaseException:
        _close(session, token)
        _wait_sync(session.close(RunOutcome.errored, None))
        raise
    _close(session, token)
    try:
        passed = _call_sync(entry.passed(session, args, kwargs, result))
    except Exception:
        log.warning("first_domino.check_failed agent=%s", entry.name, exc_info=True)
        _wait_sync(session.close(RunOutcome.errored, _final_output(result)))
        return result
    _wait_sync(session.close(_outcome(passed=passed), _final_output(result)))
    return result


def _close(session: capture.Session, token: Any) -> None:
    capture.deactivate(session)
    capture.SESSION.reset(token)


def _call_sync[T](coro: Awaitable[T]) -> T:
    """Run a coroutine from sync code, on this thread when no loop is running here."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(cast(Any, coro))
    return capture.BACKGROUND.submit(cast(Any, coro)).result()


def _timeout() -> float:
    return _CONFIG.recorder_client().settings.timeout_seconds * 2


async def _wait(future: Any) -> None:
    try:
        await asyncio.wait_for(asyncio.wrap_future(future), _timeout())
    except Exception:
        log.debug("first_domino.flush_failed", exc_info=True)


def _wait_sync(future: Any) -> None:
    try:
        future.result(timeout=_timeout())
    except Exception:
        log.debug("first_domino.flush_failed", exc_info=True)


async def replay(entry: Entrypoint, ctx: ReplayContext, client: FirstDominoClient) -> bool:
    """Run `entry` again for a replay job and return whether it passed.

    Model calls up to `ctx.from_step` are answered with the recorded outputs, the next
    with the fixed output when the job has one, and the rest by the model.
    """
    steps = await client.list_steps(ctx.job.run_id) if ctx.from_step > 0 else []
    plan = capture.ReplayPlan.of(steps, ctx.from_step, ctx.replacement_output, ctx.model_override)
    run = RecordedRun(_CONFIG.recorder_client(), ctx.run.run_id, first_step=ctx.from_step + 1)
    session = capture.Session(run, replay=plan, stop=ctx.stop)
    kwargs = entry.arguments(ctx.task_input)
    capture.install()

    def scoped[T](call: Callable[[], T]) -> T:
        token = capture.SESSION.set(session)
        try:
            return call()
        finally:
            capture.SESSION.reset(token)

    capture.activate(session)
    try:
        if entry.is_async:
            token = capture.SESSION.set(session)
            try:
                result = await entry.fn(**kwargs)
            finally:
                capture.SESSION.reset(token)
        else:
            result = await asyncio.to_thread(scoped, lambda: entry.fn(**kwargs))
    finally:
        capture.deactivate(session)
        await _wait(session.close(None, None))
    ctx.final_output = _final_output(result)
    return await entry.passed(session, (), kwargs, result)


def worker(*names: str, client: FirstDominoClient | None = None) -> Worker:
    """A `Worker` that replays the `@fd.entrypoint` functions named (default: all).

    Example:
        >>> await fd.worker().run()
    """
    api = client or default_client()
    chosen = list(names) or list(REGISTRY)
    if _CONFIG.client is None and client is not None:
        _CONFIG.client = client
    runner = Worker(agent_names=chosen, client=api)
    for name in chosen:
        entry = REGISTRY.get(name)
        if entry is None:
            continue

        async def handle(ctx: ReplayContext, entry: Entrypoint = entry) -> bool:
            return await replay(entry, ctx, api)

        def passed(_: TaskInput, result: object) -> bool:
            return result is True

        runner.agent(name)(handle)
        runner.success_check(name)(passed)
    return runner


def serve(*names: str, client: FirstDominoClient | None = None) -> None:
    """Replay your agent whenever First Domino asks, until stopped. Blocks.

    Run it in its own process next to your agent (it needs the same code, keys and
    `FIRST_DOMINO_API_KEY`). Import the module with your `@fd.entrypoint` first.

    Example:
        >>> import my_agent  # defines @fd.entrypoint("support-bot")
        >>> fd.serve()
    """
    asyncio.run(worker(*names, client=client).run())


def _hints(fn: Callable[..., Any]) -> dict[str, Any]:
    try:
        return typing.get_type_hints(fn)
    except Exception:
        return {}


def _return_type(fn: Callable[..., Any]) -> Any:
    return _hints(fn).get("return", Any)


def _as_type(content: str | None, returns: Any) -> Any:
    """A recorded tool result (text) as the type the tool returns."""
    if content is None or returns is str:
        return content
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return content
    try:
        return TypeAdapter(returns).validate_python(parsed)
    except Exception:
        return parsed
