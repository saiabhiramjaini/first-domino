"""Worker: lease replay jobs, run the customer's agent and success check, submit results."""

import asyncio
import contextlib
import inspect
import logging
import threading
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID

from first_domino._generated.models import (
    ErrorCode,
    LeaseReplayJobRequest,
    Message,
    ReplayJob,
    ReplayJobStatus,
    ReplayOutcome,
    RunOutcome,
    StartRunRequest,
    SubmitReplayResultRequest,
    TaskInput,
)
from first_domino.client import FirstDominoClient, default_client
from first_domino.errors import ApiRequestError, ConfigurationError, ReplayStopped
from first_domino.recorder import RecordedRun

log = logging.getLogger("first_domino")


class WorkerErrorCode(StrEnum):
    """Why the worker submitted a job as `errored`."""

    NO_HANDLER = "no_handler"
    START_FAILED = "start_failed"
    AGENT_FAILED = "agent_failed"
    CHECK_FAILED = "check_failed"


@dataclass(slots=True)
class ReplayContext:
    """What a replay needs: the job, and the replay run to record steps into.

    The agent continues from `messages`. When `replacement_output` is set, it uses that
    as its next step's output instead of calling the model, then continues normally.
    It may set `final_output` for the replay run. `stop` is set once First Domino no longer
    needs the replay; model calls recorded with the SDK then raise `ReplayStopped`.
    """

    job: ReplayJob
    run: RecordedRun
    final_output: str | None = field(default=None)
    stop: threading.Event = field(default_factory=threading.Event)

    @property
    def task_input(self) -> TaskInput:
        """The original run's task input."""
        return self.job.task_input

    @property
    def messages(self) -> list[Message]:
        """The conversation after `from_step`: where the replay starts."""
        return self.job.messages

    @property
    def from_step(self) -> int:
        """Steps 1..from_step are kept from the original run; 0 means start fresh."""
        return self.job.from_step

    @property
    def replacement_output(self) -> Message | None:
        """When set, the next step's output, used instead of calling the model."""
        return self.job.replacement_output

    @property
    def model_override(self) -> str | None:
        """When set, the model to run every remaining step with."""
        return self.job.model_override


type ReplayAgent[ResultT] = Callable[[ReplayContext], Awaitable[ResultT]]
type SuccessCheck[ResultT] = Callable[[TaskInput, ResultT], bool | Awaitable[bool]]


class Worker:
    """Runs replays of your agents on your side, as First Domino asks for them.

    Example:
        >>> worker = fd.Worker(agent_names=["call-assistant"])
        >>> @worker.agent("call-assistant")
        ... async def replay(ctx: fd.ReplayContext) -> CallResult: ...
        >>> @worker.success_check("call-assistant")
        ... def check(task_input: fd.TaskInput, result: CallResult) -> bool: ...
        >>> await worker.run()
    """

    def __init__(
        self, agent_names: Sequence[str], *, client: FirstDominoClient | None = None
    ) -> None:
        self._agent_names = list(agent_names)
        self._client = client or default_client()
        self._agents: dict[str, ReplayAgent[Any]] = {}
        self._checks: dict[str, SuccessCheck[Any]] = {}

    def agent[ResultT](
        self, agent_name: str
    ) -> Callable[[ReplayAgent[ResultT]], ReplayAgent[ResultT]]:
        """Register the async function that replays `agent_name` from a `ReplayContext`."""

        def register(replay: ReplayAgent[ResultT]) -> ReplayAgent[ResultT]:
            self._agents[agent_name] = replay
            return replay

        return register

    def success_check[ResultT](
        self, agent_name: str
    ) -> Callable[[SuccessCheck[ResultT]], SuccessCheck[ResultT]]:
        """Register the function that says whether a replay of `agent_name` succeeded."""

        def register(check: SuccessCheck[ResultT]) -> SuccessCheck[ResultT]:
            self._checks[agent_name] = check
            return check

        return register

    async def run(self) -> None:
        """Lease and run replay jobs forever, several at a time.

        Raises:
            ConfigurationError: No API key, or an agent name without both handlers.
        """
        self._check_configuration()
        async with asyncio.TaskGroup() as group:
            for _ in range(self._client.settings.worker_concurrency):
                group.create_task(self._loop())

    async def run_once(self) -> ReplayOutcome | None:
        """Lease one job and run it. Returns its outcome, or None when no job arrived.

        Raises:
            ApiRequestError: The lease call failed.
        """
        request = LeaseReplayJobRequest(
            agent_names=self._agent_names,
            wait_seconds=self._client.settings.lease_wait_seconds,
        )
        job = await self._client.lease_replay_job(request)
        if job is None:
            return None
        return await self._handle(job)

    def _check_configuration(self) -> None:
        if not self._client.enabled:
            msg = "FIRST_DOMINO_API_KEY is not set; the worker cannot lease jobs"
            raise ConfigurationError(msg)
        missing = [
            name
            for name in self._agent_names
            if name not in self._agents or name not in self._checks
        ]
        if missing:
            msg = f"register both @worker.agent and @worker.success_check for {missing}"
            raise ConfigurationError(msg)

    async def _loop(self) -> None:
        while True:
            try:
                await self.run_once()
            except ApiRequestError as exc:
                log.warning("first_domino.lease_failed status=%s", exc.status_code)
                await asyncio.sleep(self._client.settings.worker_retry_seconds)

    async def _handle(self, job: ReplayJob) -> ReplayOutcome:
        replay, check = self._agents.get(job.agent_name), self._checks.get(job.agent_name)
        if replay is None or check is None:
            return await self._submit(job, ReplayOutcome.errored, None, WorkerErrorCode.NO_HANDLER)
        try:
            run = await self._client.start_run(
                StartRunRequest(
                    agent_name=job.agent_name, task_input=job.task_input, replay_job_id=job.id
                )
            )
        except ApiRequestError:
            return await self._submit(
                job, ReplayOutcome.errored, None, WorkerErrorCode.START_FAILED
            )
        ctx = ReplayContext(
            job=job, run=RecordedRun(self._client, run.id, first_step=job.from_step + 1)
        )
        watch = asyncio.create_task(self._watch(ctx))
        try:
            outcome, error = await self._replay_and_check(ctx, replay, check)
        finally:
            watch.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watch
        await ctx.run.finish(RunOutcome(outcome.value), final_output=ctx.final_output)
        if ctx.stop.is_set():
            log.info("first_domino.replay_stopped job_id=%s", job.id)
            return outcome
        return await self._submit(job, outcome, run.id, error)

    async def _watch(self, ctx: ReplayContext) -> None:
        """Sets `ctx.stop` once the job is ended, or leased again after this lease ran out."""
        while True:
            await asyncio.sleep(self._client.settings.job_check_seconds)
            try:
                job = await self._client.get_replay_job(ctx.job.id)
            except ApiRequestError:
                continue
            if job.status is not ReplayJobStatus.leased or job.attempt != ctx.job.attempt:
                ctx.stop.set()
                return

    async def _replay_and_check(
        self, ctx: ReplayContext, replay: ReplayAgent[Any], check: SuccessCheck[Any]
    ) -> tuple[ReplayOutcome, WorkerErrorCode | None]:
        try:
            result = await replay(ctx)
        except ReplayStopped:
            return ReplayOutcome.errored, None
        except Exception:
            log.exception("first_domino.replay_agent_failed job_id=%s", ctx.job.id)
            return ReplayOutcome.errored, WorkerErrorCode.AGENT_FAILED
        try:
            verdict = check(ctx.task_input, result)
            passed = await verdict if inspect.isawaitable(verdict) else verdict
        except Exception:
            log.exception("first_domino.success_check_failed job_id=%s", ctx.job.id)
            return ReplayOutcome.errored, WorkerErrorCode.CHECK_FAILED
        return (ReplayOutcome.passed if passed else ReplayOutcome.failed), None

    async def _submit(
        self,
        job: ReplayJob,
        outcome: ReplayOutcome,
        run_id: UUID | None,
        error: WorkerErrorCode | None,
    ) -> ReplayOutcome:
        request = SubmitReplayResultRequest(
            replay_job_id=job.id,
            outcome=outcome,
            replay_run_id=run_id,
            error_code=ErrorCode(error.value) if error else None,
        )
        try:
            await self._client.submit_replay_result(request)
        except ApiRequestError as exc:
            log.warning("first_domino.submit_failed job_id=%s status=%s", job.id, exc.status_code)
        log.info("first_domino.replay_finished job_id=%s outcome=%s", job.id, outcome)
        return outcome
