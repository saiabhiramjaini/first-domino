"""Fakes for the engine ports: scripted replays, an in-memory sink and reader."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from pydantic import BaseModel

from fd_engine.errors import LlmCallError
from fd_engine.explain import ExplainedStep, unexplained
from fd_engine.judge import JudgedReplay
from fd_engine.llm import RawCompletion
from fd_engine.settings import EngineSettings
from fd_engine.verify import FixedStep
from fd_shared.enums import DiagnosisStatus, MessageRole, ReplayOutcome, RunStatus
from fd_shared.models import (
    CheckView,
    Message,
    ReplayDrift,
    ReplayResult,
    RunView,
    StepView,
    TaskInput,
    ToolCall,
)

P = ReplayOutcome.PASSED
F = ReplayOutcome.FAILED
E = ReplayOutcome.ERRORED
D = ReplayResult(outcome=ReplayOutcome.PASSED, drift=ReplayDrift(step=1, tool_name="lookup"))
"""A replay that drifted from the recording at step 1, in the `lookup` tool."""

Scripted = ReplayOutcome | ReplayResult
"""A scripted replay: a bare outcome is one that reproduced the recording."""


def as_result(scripted: Scripted) -> ReplayResult:
    if isinstance(scripted, ReplayResult):
        return scripted
    return ReplayResult(outcome=scripted)


TEST_MODEL = "strong-test-model"


def settings(**overrides: object) -> EngineSettings:
    values: dict[str, object] = {
        "strong_model": TEST_MODEL,
        "samples_per_check": 3,
        "doomed_recheck_samples": 0,
        "verify_samples": 5,
        "verify_pass_threshold": 3,
        "fallback_window": 2,
        "max_checks": 24,
        "replay_timeout_seconds": 5.0,
    }
    values.update(overrides)
    return EngineSettings.model_validate(values)


Script = Callable[[int], list[Scripted]]
"""Outcomes for a replay from a save point, given the save point."""


def break_at(step: int, samples: int = 3) -> Script:
    """The run can succeed from save points before `step` and is doomed from `step` on."""
    return lambda save_point: [P] * samples if save_point < step else [F] * samples


@dataclass
class ReplayCall:
    from_step: int
    samples: int
    model_override: str | None
    replacement_output: Message | None


@dataclass
class FakeRunner:
    """Scripted outcomes: `plain` for unfixed replays, `fixed[step]` for a fix of `step`.

    Successive replays from the same save point get the script's outcomes in order, so a check
    made of one-replay calls sees the same outcomes as one call for all its samples.
    """

    plain: Script
    fixed: dict[int, list[Scripted]] = field(default_factory=dict)
    delay_seconds: float = 0.0
    calls: list[ReplayCall] = field(default_factory=list)
    served: dict[tuple[int, bool], int] = field(default_factory=dict)

    async def replay(
        self,
        run_id: UUID,
        *,
        from_step: int,
        samples: int,
        model_override: str | None,
        replacement_output: Message | None,
    ) -> list[ReplayResult]:
        self.calls.append(ReplayCall(from_step, samples, model_override, replacement_output))
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        fixed = replacement_output is not None
        script = self.fixed.get(from_step + 1, [F]) if fixed else self.plain(from_step)
        start = self.served.get((from_step, fixed), 0)
        self.served[(from_step, fixed)] = start + samples
        return [as_result(script[(start + offset) % len(script)]) for offset in range(samples)]


@dataclass
class ProgressEvent:
    status: DiagnosisStatus
    search_low: int | None
    search_high: int | None


@dataclass
class FakeSink:
    started: list[CheckView] = field(default_factory=list)
    finished: list[CheckView] = field(default_factory=list)
    progress_events: list[ProgressEvent] = field(default_factory=list)
    costs: list[float] = field(default_factory=list)

    async def check_started(self, check: CheckView) -> None:
        self.started.append(check)

    async def check_finished(self, check: CheckView) -> None:
        self.finished.append(check)

    async def cost_added(self, diagnosis_id: UUID, cost_usd: float) -> None:
        self.costs.append(cost_usd)

    async def progress(
        self,
        diagnosis_id: UUID,
        *,
        status: DiagnosisStatus,
        search_low: int | None,
        search_high: int | None,
    ) -> None:
        self.progress_events.append(ProgressEvent(status, search_low, search_high))


def tool_step(index: int, tool: str | None = None) -> StepView:
    """A recorded step that calls one tool, `tool_<index>` unless named."""
    call = ToolCall(id=f"c{index}", name=tool or f"tool_{index}", arguments="{}")
    return StepView(
        index=index,
        model="agent-test-model",
        output=Message(role=MessageRole.ASSISTANT, content=None, tool_calls=[call]),
        tool_results=[],
    )


@dataclass
class FakeReader:
    """The failed run, flagged when `failure_reason` is set, and the replay runs it was given.

    A replay run has no steps of its own unless `replay_steps` names some.
    """

    step_count: int
    run_id: UUID = field(default_factory=uuid4)
    failure_reason: str | None = None
    replay_outputs: dict[UUID, str] = field(default_factory=dict)
    replay_steps: dict[UUID, list[StepView]] = field(default_factory=dict)

    async def get_run(self, run_id: UUID) -> RunView:
        if run_id in self.replay_outputs:
            return RunView(
                id=run_id,
                agent_name="test-agent",
                task_input=TaskInput(prompt="book a visit"),
                status=RunStatus.PASSED,
                step_count=len(self.replay_steps.get(run_id, [])),
                final_output=self.replay_outputs[run_id],
            )
        return RunView(
            id=run_id,
            agent_name="test-agent",
            task_input=TaskInput(prompt="book a visit"),
            status=RunStatus.FAILED,
            step_count=self.step_count,
            final_output="booked the wrong visit",
            failure_reason=self.failure_reason,
            flagged=self.failure_reason is not None,
        )

    async def get_steps(self, run_id: UUID) -> list[StepView]:
        if run_id in self.replay_outputs:
            return self.replay_steps.get(run_id, [])
        return [tool_step(index) for index in range(1, self.step_count + 1)]


@dataclass
class BlindWorker:
    """A worker whose check cannot see a flagged run's failure: every replay that ran passes.

    The scripted outcome becomes the replay run's final output, for `FakeJudge` to read.
    """

    runner: FakeRunner
    reader: FakeReader

    async def replay(
        self,
        run_id: UUID,
        *,
        from_step: int,
        samples: int,
        model_override: str | None,
        replacement_output: Message | None,
    ) -> list[ReplayResult]:
        results = await self.runner.replay(
            run_id,
            from_step=from_step,
            samples=samples,
            model_override=model_override,
            replacement_output=replacement_output,
        )
        return [self._seen_by_the_worker(result) for result in results]

    def _seen_by_the_worker(self, result: ReplayResult) -> ReplayResult:
        if result.outcome is ReplayOutcome.ERRORED:
            return result
        replay_run_id = uuid4()
        self.reader.replay_outputs[replay_run_id] = result.outcome.value
        return result.model_copy(
            update={"outcome": ReplayOutcome.PASSED, "replay_run_id": replay_run_id}
        )


@dataclass
class FakeJudge:
    """Decides a replay from its run's final output, the outcome `BlindWorker` hid there.

    With `degraded`, every decision is unusable and the replay is `errored`.
    """

    cost_usd: float = 0.005
    degraded: bool = False
    judged: list[list[StepView]] = field(default_factory=list)

    async def judge(
        self, run: RunView, replay: RunView, replay_steps: list[StepView]
    ) -> JudgedReplay:
        self.judged.append(replay_steps)
        hidden = ReplayOutcome(replay.final_output or ReplayOutcome.ERRORED)
        outcome = ReplayOutcome.ERRORED if self.degraded else hidden
        return JudgedReplay(outcome=outcome, reason="scripted", cost_usd=self.cost_usd)


@dataclass
class FakeFixer:
    """Returns a fixed output for every step, or None for steps in `unfixable`."""

    unfixable: set[int] = field(default_factory=set)
    cost_usd: float = 0.01

    async def fix(self, run: RunView, steps: list[StepView], step_index: int) -> FixedStep:
        if step_index in self.unfixable:
            return FixedStep(output=None, cost_usd=self.cost_usd)
        output = Message(role=MessageRole.ASSISTANT, content=f"fixed step {step_index}")
        return FixedStep(output=output, cost_usd=self.cost_usd)


@dataclass
class FakeExplainer:
    cost_usd: float = 0.02
    explained: list[int] = field(default_factory=list)

    async def explain(
        self, run: RunView, steps: list[StepView], step: int, fixed_output: Message | None
    ) -> ExplainedStep:
        self.explained.append(step)
        return ExplainedStep(explanation=unexplained(step), cost_usd=self.cost_usd)


@dataclass
class FakeTransport:
    """Returns scripted reply texts in order; None in the script means the call failed."""

    replies: list[str | None]
    tokens_in: int = 1000
    tokens_out: int = 100
    prompts: list[str] = field(default_factory=list)
    models: list[str | None] = field(default_factory=list)
    temperatures: list[float | None] = field(default_factory=list)

    async def complete(
        self,
        *,
        system: str,
        user: str,
        schema: type[BaseModel],
        timeout_seconds: float,
        model: str | None = None,
        temperature: float | None = None,
    ) -> RawCompletion:
        self.prompts.append(user)
        self.models.append(model)
        self.temperatures.append(temperature)
        reply = self.replies.pop(0)
        if reply is None:
            raise LlmCallError
        return RawCompletion(content=reply, tokens_in=self.tokens_in, tokens_out=self.tokens_out)
