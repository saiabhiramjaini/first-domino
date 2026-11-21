"""Rewrite the found step and replay to prove that it flips the outcome."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from fd_engine.checks import CheckRequest, CheckRunner
from fd_engine.models import CheckPhase, Message, RunView, StepView
from fd_engine.settings import EngineSettings


class FixedStep(BaseModel):
    """A rewritten model output for one step, or None when no usable fix came back."""

    model_config = ConfigDict(frozen=True)

    output: Message | None
    cost_usd: float = Field(ge=0)


class StepFixer(Protocol):
    """Writes a corrected model output for one step of a failed run."""

    async def fix(self, run: RunView, steps: list[StepView], step_index: int) -> FixedStep:
        """Return a corrected output for step `step_index`, given the steps before it."""
        ...


class FixAttempt(BaseModel):
    """The result of fixing one step and replaying from it."""

    model_config = ConfigDict(frozen=True)

    step: int
    fixed_output: Message | None
    passes: int | None
    samples: int | None
    verified: bool
    cost_usd: float = Field(ge=0)


class Verifier:
    """Proves a step is the first domino by fixing it and replaying with the agent's own model."""

    def __init__(
        self,
        *,
        checks: CheckRunner,
        fixer: StepFixer,
        settings: EngineSettings,
    ) -> None:
        self._checks = checks
        self._fixer = fixer
        self._settings = settings

    async def try_fix(
        self,
        run: RunView,
        steps: list[StepView],
        step: int,
        phase: CheckPhase,
    ) -> FixAttempt:
        """Fix `step` and replay from it.

        Verified only when at least `verify_pass_threshold` of `verify_samples` replays pass.
        Without a usable fix there is no replay, and the attempt is unverified.
        """
        fixed = await self._fixer.fix(run, steps, step)
        if fixed.output is None:
            return FixAttempt(
                step=step,
                fixed_output=None,
                passes=None,
                samples=None,
                verified=False,
                cost_usd=fixed.cost_usd,
            )
        check = await self._checks.run(
            CheckRequest(
                phase=phase,
                save_point=step - 1,
                samples=self._settings.verify_samples,
                required_passes=self._settings.verify_pass_threshold,
                replacement_output=fixed.output,
            )
        )
        return FixAttempt(
            step=step,
            fixed_output=fixed.output,
            passes=check.passes,
            samples=check.samples,
            verified=check.passes >= self._settings.verify_pass_threshold,
            cost_usd=fixed.cost_usd,
        )
