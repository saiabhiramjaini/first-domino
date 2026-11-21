"""Engine port adapters that replay the demo agent in this process instead of over HTTP.

The benchmark uses them so it measures the engine, not the job queue. Replays still run the
real agent loop with the real model and the call's own success check.
"""

import asyncio
from collections import defaultdict
from uuid import UUID

from openai import OpenAIError

from fd_demo_agent.agent import CallAgent
from fd_demo_agent.prompts import opening_messages
from fd_demo_agent.success import check_call
from fd_demo_agent.tasks import get_task
from fd_demo_agent.world import load_world
from fd_engine.llm import LlmUsage
from fd_engine.settings import EngineSettings
from fd_scripts.convert import assistant_param, conversation
from fd_scripts.dataset import LabelledRun
from fd_scripts.settings import ScriptsSettings
from fd_shared.enums import DiagnosisStatus, ReplayOutcome
from fd_shared.logging import get_logger
from fd_shared.models import CheckView, Message, RunView, StepView

log = get_logger(__name__)

_MILLION = 1_000_000


class DatasetReader:
    """`RunReader` over the labelled runs."""

    def __init__(self, cases: dict[UUID, LabelledRun]) -> None:
        self._cases = cases

    async def get_run(self, run_id: UUID) -> RunView:
        """The labelled run."""
        return self._cases[run_id].run

    async def get_steps(self, run_id: UUID) -> list[StepView]:
        """The labelled run's steps."""
        return self._cases[run_id].steps


class DiscardingSink:
    """`CheckSink` that keeps nothing: the benchmark scores only the final result."""

    async def check_started(self, check: CheckView) -> None:
        """Ignore the check."""

    async def check_finished(self, check: CheckView) -> None:
        """Ignore the check."""

    async def progress(
        self,
        diagnosis_id: UUID,
        *,
        status: DiagnosisStatus,
        search_low: int | None,
        search_high: int | None,
    ) -> None:
        """Ignore the progress."""


class DemoReplayRunner:
    """`ReplayRunner` that runs the demo agent from a save point and applies its success check.

    It also adds up the tokens every replay spends, per run, so the benchmark can charge
    replays to the engine's cost.
    """

    def __init__(
        self,
        agent: CallAgent,
        cases: dict[UUID, LabelledRun],
        limit: asyncio.Semaphore,
        engine_settings: EngineSettings,
        scripts_settings: ScriptsSettings,
    ) -> None:
        self._agent = agent
        self._cases = cases
        self._limit = limit
        self._engine_settings = engine_settings
        self._scripts_settings = scripts_settings
        self._usage: defaultdict[UUID, LlmUsage] = defaultdict(LlmUsage)

    def usage(self, run_id: UUID) -> LlmUsage:
        """Tokens and cost of every replay of `run_id` so far."""
        return self._usage[run_id]

    async def replay(
        self,
        run_id: UUID,
        *,
        from_step: int,
        samples: int,
        model_override: str | None,
        replacement_output: Message | None,
    ) -> list[ReplayOutcome]:
        """Run `samples` replays at once and return each one's outcome."""
        replays = (
            self._replay_once(run_id, from_step, model_override, replacement_output)
            for _ in range(samples)
        )
        return list(await asyncio.gather(*replays))

    async def _replay_once(
        self,
        run_id: UUID,
        from_step: int,
        model_override: str | None,
        replacement_output: Message | None,
    ) -> ReplayOutcome:
        case = self._cases[run_id]
        task = get_task(case.task_id)
        start = conversation(opening_messages(task, load_world().user), case.steps[:from_step])
        replacement = assistant_param(replacement_output) if replacement_output else None
        async with self._limit:
            try:
                result = await self._agent.run(
                    task, start, replacement_output=replacement, model_override=model_override
                )
            except OpenAIError as error:
                log.warning("replay.errored", case_id=case.case_id, error=type(error).__name__)
                return ReplayOutcome.ERRORED
        tokens_in = sum(step.tokens_in for step in result.steps)
        tokens_out = sum(step.tokens_out for step in result.steps)
        usage = self._price(tokens_in, tokens_out, on_strong_model=model_override is not None)
        self._usage[run_id] = self._usage[run_id].plus(usage)
        passed = check_call(task, result.outcome).passed
        return ReplayOutcome.PASSED if passed else ReplayOutcome.FAILED

    def _price(self, tokens_in: int, tokens_out: int, *, on_strong_model: bool) -> LlmUsage:
        engine, scripts = self._engine_settings, self._scripts_settings
        price_in, price_out = (
            (engine.llm_input_usd_per_million_tokens, engine.llm_output_usd_per_million_tokens)
            if on_strong_model
            else (
                scripts.agent_input_usd_per_million_tokens,
                scripts.agent_output_usd_per_million_tokens,
            )
        )
        cost = (tokens_in * price_in + tokens_out * price_out) / _MILLION
        return LlmUsage(tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost)
