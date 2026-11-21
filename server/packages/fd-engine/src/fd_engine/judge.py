"""Judges one replay of a flagged run against the failure a person reported, with one model call.

A flagged run passed the customer's success check, so that check cannot see its failure and
would pass every replay. For these runs, and only these, the engine decides each replay's
outcome itself, from the reported `failure_reason`.
"""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from fd_engine.llm import Llm
from fd_engine.transcript import render_steps, render_task
from fd_shared.enums import ReplayOutcome
from fd_shared.models import RunView, StepView

_SYSTEM = """\
You judge one replay of an AI agent run.
A person reported that the original run failed, and said what went wrong. Treat that report as
the truth about the original run, even if the original output looks fine to you.
The replay ran the same task again. It may keep some of the original turns and continue from
there with new ones. Decide whether the replay completed the task without the reported problem.
- The replay fails when the reported problem happens again, even in other words, with other
  values or at a different point.
- The replay fails when it does the same thing the original run did: the same actions, the same
  decisions or, in substance, the same final output. Doing what the original did repeats its
  failure.
- The replay fails when it avoids the reported problem but fails the task another way: it stops
  early, leaves the task unfinished, breaks an explicit requirement of the task, or states or
  uses facts it was not given.
- The replay passes only when it completes the task and the reported problem is absent.
- Judge only from the transcript and the final output shown. Do not assume actions that are not
  shown.
Return JSON: "passed" (true or false) and "reason" (one sentence naming what in the replay
decided it). Use US English. Do not use em dashes.
"""

_NONE = "(none)"


class JudgeReply(BaseModel):
    """The judge's decision. `passed` is None only in the fallback for an unusable reply."""

    passed: bool | None = None
    reason: str = ""


class JudgedReplay(BaseModel):
    """A replay's outcome as the judge decided it, and what the decision cost.

    `errored` means the judge gave no usable decision, so the replay is not evidence.
    """

    model_config = ConfigDict(frozen=True)

    outcome: ReplayOutcome
    reason: str
    cost_usd: float = Field(ge=0)


class ReplayJudge(Protocol):
    """Decides whether a replay of a flagged run still has the reported failure."""

    async def judge(
        self, run: RunView, replay: RunView, replay_steps: list[StepView]
    ) -> JudgedReplay:
        """Judge `replay` of `run` from the replay's whole transcript.

        Never raises on a bad model reply; that replay is `errored` instead.
        """
        ...


class LlmReplayJudge:
    """A `ReplayJudge` backed by one structured model call."""

    def __init__(
        self, llm: Llm, *, model: str | None = None, temperature: float | None = None
    ) -> None:
        self._llm = llm
        self._model = model
        self._temperature = temperature

    async def judge(
        self, run: RunView, replay: RunView, replay_steps: list[StepView]
    ) -> JudgedReplay:
        """Judge the replay; a reply with no usable `passed` makes it `errored`."""
        reply = await self._llm.structured(
            system=_SYSTEM,
            user=_prompt(run, replay, replay_steps),
            schema=JudgeReply,
            fallback=JudgeReply(),
            model=self._model,
            temperature=self._temperature,
        )
        cost = reply.usage.cost_usd
        if reply.value.passed is None:
            return JudgedReplay(outcome=ReplayOutcome.ERRORED, reason="", cost_usd=cost)
        outcome = ReplayOutcome.PASSED if reply.value.passed else ReplayOutcome.FAILED
        return JudgedReplay(outcome=outcome, reason=reply.value.reason, cost_usd=cost)


def _prompt(run: RunView, replay: RunView, replay_steps: list[StepView]) -> str:
    return "\n\n".join(
        [
            render_task(run),
            "# Final output of the original run (it has the reported problem)",
            run.final_output or _NONE,
            "# The replay",
            render_steps(replay_steps) or _NONE,
            "# Final output of the replay",
            replay.final_output or _NONE,
        ]
    )
