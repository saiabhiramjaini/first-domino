"""Plain-language cause, category and suggested fix for a verified step."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from fd_engine.llm import Llm
from fd_engine.transcript import render_message, render_steps, render_task
from fd_shared.enums import CauseCategory
from fd_shared.models import Explanation, Message, RunView, StepView

_SYSTEM = """\
You explain why an AI agent run failed, for the engineer who owns the agent.
Replays point to step {step} as the first mistake: before it the run can still succeed, and
with it kept the run is doomed. You get the run, the original step and the rewritten step that
was replayed to test a fix. The difference between the two is usually the mistake.
Return JSON:
- "title": at most 8 words naming the concrete mistake: the action and what was wrong, with the
  wrong and right value when they are short. Start with a past-tense verb for what the agent
  did. Good: "Booked 22:00 instead of 10:00", "Read the OTP aloud to a scam caller", "Set the
  reminder a day early", "Left the reports note off the booking", "Scheduled a callback for a
  spam caller". Bad: "Failed to confirm caller request", "Incorrect event details", "Mishandled
  the call". Never start with "Failed to", "Incorrect" or "Wrong", and leave out names of people
  and calendar dates.
- "summary": two sentences. First what the agent did at step {step} and what it should have
  done, with the concrete values. Then why that doomed the run.
- "suggested_fix": one or two sentences on what to change in the agent: its prompt, a tool, or a
  check before acting.
- "category": exactly one of these values:
{categories}
Use US English. Do not use em dashes.
"""

_CATEGORY_MEANINGS: dict[CauseCategory, str] = {
    CauseCategory.WRONG_DATE: "a date, time or time offset resolved or written wrong (relative "
    "dates, AM and PM, reminder lead time)",
    CauseCategory.WRONG_ENTITY: "acted on the wrong person, contact, phone number or event "
    "(similar names, callback for the wrong person)",
    CauseCategory.WRONG_FILTER: "looked up the wrong thing or too narrowly, so it missed what it "
    "needed (memory search, calendar check, contact lookup)",
    CauseCategory.BAD_TOOL_ARGS: "the right action with missing or wrong details (notes left "
    "out, a required field dropped)",
    CauseCategory.HALLUCINATION: "stated or used a fact that is not in the conversation or the "
    "user's data",
    CauseCategory.TOOL_ISSUE: "a tool failed or returned wrong data and the agent could not "
    "recover",
    CauseCategory.OTHER: "the wrong decision about what to do (a spam caller treated as genuine, "
    "private data such as an OTP shared with a caller) or anything else",
}


_CATEGORY_LINES = "\n".join(
    f"  - {category.value}: {_CATEGORY_MEANINGS[category]}" for category in CauseCategory
)


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
            system=_SYSTEM.format(step=step, categories=_CATEGORY_LINES),
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
