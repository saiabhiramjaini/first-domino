"""Read-the-trace baseline judge, used only by the benchmark."""

from pydantic import BaseModel, ConfigDict, Field

from fd_engine.llm import Llm
from fd_engine.transcript import render_steps, render_task
from fd_shared.models import RunView, StepView

_SYSTEM = """\
You review a failed AI agent run. Find the first step where the agent made the mistake that
doomed the run: after that step, no later choice could have saved it.
Return JSON with "step" (the step number) and "reason" (one sentence).
"""


class JudgeReply(BaseModel):
    """The judge's pick."""

    step: int | None = None
    reason: str = ""


class BaselinePrediction(BaseModel):
    """The step the judge blamed, or None when its reply was unusable."""

    model_config = ConfigDict(frozen=True)

    step: int | None
    reason: str
    cost_usd: float = Field(ge=0)


class BaselineJudge:
    """Reads the whole trace once and names the first doomed step. No replays, no proof."""

    def __init__(self, llm: Llm) -> None:
        self._llm = llm

    async def predict(self, run: RunView, steps: list[StepView]) -> BaselinePrediction:
        """Return the judge's step, or None when it names no step of this run."""
        reply = await self._llm.structured(
            system=_SYSTEM,
            user="\n\n".join([render_task(run), "# The run (it failed)", render_steps(steps)]),
            schema=JudgeReply,
            fallback=JudgeReply(),
        )
        step = reply.value.step
        in_range = step is not None and any(s.index == step for s in steps)
        return BaselinePrediction(
            step=step if in_range else None,
            reason=reply.value.reason,
            cost_usd=reply.usage.cost_usd,
        )
