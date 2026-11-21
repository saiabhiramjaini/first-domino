"""Plain-language cause, category and suggested fix for a verified step."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from fd_engine.llm import Llm
from fd_engine.models import CauseCategory, Explanation, Message, RunView, StepView
from fd_engine.transcript import render_message, render_steps, render_task

_SYSTEM = """\
You explain why an AI agent run failed, for the engineer who owns the agent.
Replays proved that step {step} is the first mistake: before it the run can still succeed, and
with it kept the run is doomed. You get the run, the original step and the rewritten step that
was replayed to test the fix.
Return JSON:
- "title": at most 8 words naming the mistake, such as "Booked the wrong date".
- "summary": two sentences on what the agent did wrong at step {step} and why it doomed the run.
- "suggested_fix": one or two sentences on what to change in the agent (prompt, tool, check).
- "category": one of {categories}.
Use US English. Do not use em dashes.
"""


class ExplainedStep(BaseModel):
    """An explanation and what it cost."""

    model_config = ConfigDict(frozen=True)

    explanation: Explanation
    cost_usd: float = Field(ge=0)


class StepExplainer(Protocol):
    """Explains why a step doomed the run."""

    async def explain(
        self, run: RunView, steps: list[StepView], step: int, fixed_output: Message | None
    ) -> ExplainedStep:
        """Return an explanation of step `step`. Never raises on a bad model reply."""
        ...


def unexplained(step: int) -> Explanation:
    """The explanation used when the model gives nothing usable."""
    return Explanation(
        title=f"Unexplained mistake at step {step}",
        summary=f"Replays show the run became doomed at step {step}, but no explanation was "
        "produced.",
        suggested_fix=f"Review step {step} of the run.",
        category=CauseCategory.OTHER,
    )


class LlmExplainer:
    """A `StepExplainer` backed by one structured model call."""

    def __init__(self, llm: Llm) -> None:
        self._llm = llm

    async def explain(
        self, run: RunView, steps: list[StepView], step: int, fixed_output: Message | None
    ) -> ExplainedStep:
        """Explain step `step`, salvaging or degrading to `unexplained` on a bad reply."""
        reply = await self._llm.structured(
            system=_SYSTEM.format(
                step=step, categories=", ".join(category.value for category in CauseCategory)
            ),
            user=_prompt(run, steps, step, fixed_output),
            schema=Explanation,
            fallback=unexplained(step),
        )
        return ExplainedStep(explanation=reply.value, cost_usd=reply.usage.cost_usd)


def _prompt(run: RunView, steps: list[StepView], step: int, fixed_output: Message | None) -> str:
    fixed = render_message(fixed_output) if fixed_output else "(no rewrite was produced)"
    return "\n\n".join(
        [
            render_task(run),
            "# The run (it failed)",
            render_steps(steps),
            f"# Rewritten step {step} used to test the fix",
            fixed,
        ]
    )
