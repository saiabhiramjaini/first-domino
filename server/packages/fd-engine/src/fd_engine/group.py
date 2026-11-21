"""Attach a cause to a matching cause group or start a new one.

A cause is keyed on its category and the tool its failing step called. Only existing causes with
the same key are offered to the model, which then merges only the same specific mistake.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from fd_engine.llm import Llm
from fd_shared.enums import CauseCategory
from fd_shared.models import Explanation

_SYSTEM = """\
You group root causes of failed AI agent runs. Every existing cause you get already has the same
category and failing tool as the new cause, so match on the mistake itself.
Two causes match only when they are the same specific mistake, so the same small change to the
agent fixes both. Details such as names, dates and values may differ.
- Match: "Resolved 'tomorrow' one day late" in one run and "Booked the day after tomorrow for
  'tomorrow'" in another.
- Do not match: "Resolved 'tomorrow' one day late" and "Booked 22:00 instead of 10:00". Both are
  wrong dates on the same tool, but they are different mistakes with different fixes.
- Do not match: a dropped note and a wrong time on the same event.
When in doubt, do not match.
You get a new cause and a numbered list of existing causes. Return JSON with "match": the number
of the existing cause it matches, or null when none matches.
"""


class CauseCandidate(BaseModel):
    """An existing cause group the new cause may belong to."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str
    category: CauseCategory
    step_name: str
    """The tool the cause's failing step called, or the step's role when it called none."""
    summary: str


class CauseMatch(BaseModel):
    """The existing cause to attach to, or None to start a new one."""

    model_config = ConfigDict(frozen=True)

    cause_id: UUID | None
    cost_usd: float = Field(ge=0)


class GroupReply(BaseModel):
    """The model's choice, as a 1-based number in the candidate list."""

    match: int | None = None


class CauseGrouper:
    """Matches a new explanation to one of the project's existing causes."""

    def __init__(self, llm: Llm) -> None:
        self._llm = llm

    async def match(
        self, explanation: Explanation, candidates: list[CauseCandidate], *, step_name: str
    ) -> CauseMatch:
        """Return the matching cause, or None when there is none or the reply is unusable.

        Args:
            explanation: The new cause.
            candidates: The project's existing causes.
            step_name: The tool the new cause's failing step called (see `CauseCandidate`).
        """
        keyed = same_key(explanation, candidates, step_name=step_name)
        if not keyed:
            return CauseMatch(cause_id=None, cost_usd=0.0)
        reply = await self._llm.structured(
            system=_SYSTEM,
            user=_prompt(explanation, keyed),
            schema=GroupReply,
            fallback=GroupReply(),
        )
        number = reply.value.match
        cause_id = (
            keyed[number - 1].id if number is not None and 1 <= number <= len(keyed) else None
        )
        return CauseMatch(cause_id=cause_id, cost_usd=reply.usage.cost_usd)


def same_key(
    explanation: Explanation, candidates: list[CauseCandidate], *, step_name: str
) -> list[CauseCandidate]:
    """The candidates with the new cause's category and failing tool, in their original order."""
    return [
        candidate
        for candidate in candidates
        if candidate.category is explanation.category and candidate.step_name == step_name
    ]


def _describe(title: str, category: CauseCategory, summary: str) -> str:
    return f"{title} [{category.value}]: {summary}"


def _prompt(explanation: Explanation, candidates: list[CauseCandidate]) -> str:
    lines = [
        "# New cause",
        _describe(explanation.title, explanation.category, explanation.summary),
        "# Existing causes",
    ]
    lines.extend(
        f"{number}. {_describe(cause.title, cause.category, cause.summary)}"
        for number, cause in enumerate(candidates, start=1)
    )
    return "\n".join(lines)
