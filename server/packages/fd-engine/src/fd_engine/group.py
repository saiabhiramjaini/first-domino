"""Attach a cause to a matching cause group or start a new one."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from fd_engine.llm import Llm
from fd_shared.enums import CauseCategory
from fd_shared.models import Explanation

_SYSTEM = """\
You group root causes of failed AI agent runs. Two causes match when the same change to the agent
would fix both, even if the details (names, dates, values) differ.
You get a new cause and a numbered list of existing causes. Return JSON with "match": the number
of the existing cause it matches, or null when none matches.
"""


class CauseCandidate(BaseModel):
    """An existing cause group the new cause may belong to."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str
    category: CauseCategory
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

    async def match(self, explanation: Explanation, candidates: list[CauseCandidate]) -> CauseMatch:
        """Return the matching cause, or None when there is none or the reply is unusable."""
        if not candidates:
            return CauseMatch(cause_id=None, cost_usd=0.0)
        reply = await self._llm.structured(
            system=_SYSTEM,
            user=_prompt(explanation, candidates),
            schema=GroupReply,
            fallback=GroupReply(),
        )
        number = reply.value.match
        cause_id = (
            candidates[number - 1].id
            if number is not None and 1 <= number <= len(candidates)
            else None
        )
        return CauseMatch(cause_id=cause_id, cost_usd=reply.usage.cost_usd)


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
