"""Writes a corrected model output for the suspected step, for verify and fallback to replay."""

import json
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from fd_engine.llm import Llm, ReplyQuality
from fd_engine.models import Message, MessageRole, RunView, StepView, ToolCall
from fd_engine.transcript import render_steps, render_task
from fd_engine.verify import FixedStep

_SYSTEM = """\
You repair one turn of a failed AI agent run.
Replays show the run can still succeed before step {step} and is doomed once step {step} is kept,
so step {step} is where it went wrong. Rewrite only the assistant turn at step {step} so the agent
can still complete the task.
- If the original turn called tools, call the tools it should have called, with corrected
  arguments. Use only tool names that appear in the run.
- Keep the agent's voice and format. Do not finish the task in this one turn unless the original
  turn was the last one.
- Return JSON: "content" (text or null) and "tool_calls" (a list of objects with "name" and
  "arguments", where "arguments" is a JSON object written as a string).
"""

_TOOL_CALL_ID_PREFIX = "call_fd_"


class ToolCallDraft(BaseModel):
    """A tool call in the rewritten turn, before it gets an id."""

    name: str = Field(min_length=1)
    arguments: str

    @field_validator("arguments")
    @classmethod
    def _is_json_object(cls, value: str) -> str:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as error:
            msg = "arguments must be JSON text"
            raise ValueError(msg) from error
        if not isinstance(parsed, dict):
            msg = "arguments must be a JSON object"
            raise ValueError(msg)
        return value


class FixReply(BaseModel):
    """The model's rewritten assistant turn."""

    content: str | None = None
    tool_calls: list[ToolCallDraft] = Field(default_factory=list)


class LlmStepFixer:
    """A `StepFixer` that asks the strong model for the corrected turn."""

    def __init__(self, llm: Llm) -> None:
        self._llm = llm

    async def fix(self, run: RunView, steps: list[StepView], step_index: int) -> FixedStep:
        """Return the rewritten turn, or no output when the reply was not fully usable."""
        reply = await self._llm.structured(
            system=_SYSTEM.format(step=step_index),
            user=_prompt(run, steps, step_index),
            schema=FixReply,
            fallback=FixReply(),
        )
        cost = reply.usage.cost_usd
        fix = reply.value
        if reply.quality is not ReplyQuality.PARSED or not (fix.content or fix.tool_calls):
            return FixedStep(output=None, cost_usd=cost)
        return FixedStep(output=_to_message(fix), cost_usd=cost)


def _prompt(run: RunView, steps: list[StepView], step_index: int) -> str:
    before = [step for step in steps if step.index < step_index]
    target = [step for step in steps if step.index == step_index]
    after = [step for step in steps if step.index > step_index]
    return "\n\n".join(
        [
            render_task(run),
            "# Steps before the mistake",
            render_steps(before) or "(none)",
            "# The turn to rewrite",
            render_steps(target),
            "# What happened after it (the run failed)",
            render_steps(after) or "(none)",
        ]
    )


def _to_message(fix: FixReply) -> Message:
    return Message(
        role=MessageRole.ASSISTANT,
        content=fix.content,
        tool_calls=[
            ToolCall(
                id=f"{_TOOL_CALL_ID_PREFIX}{uuid4().hex[:24]}",
                name=call.name,
                arguments=call.arguments,
            )
            for call in fix.tool_calls
        ],
    )
