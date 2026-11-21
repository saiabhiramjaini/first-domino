"""The agent loop: one model turn plus its tool results per step."""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from time import perf_counter

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionToolMessageParam,
)

from fd_demo_agent.llm import ChatModel, ModelTurn
from fd_demo_agent.messages import assistant_messages, function_calls, text_of
from fd_demo_agent.sandbox import CallOutcome
from fd_demo_agent.settings import DemoAgentSettings
from fd_demo_agent.tasks import CallTask
from fd_demo_agent.toolbox import ToolBox, tool_specs
from fd_demo_agent.world import World, load_world


class StopReason(StrEnum):
    """Why a run ended."""

    FINAL_ANSWER = "final_answer"
    STEP_LIMIT = "step_limit"


@dataclass(frozen=True, slots=True)
class AgentStep:
    """One step, which is also a save point: `messages` is the conversation after it."""

    index: int
    model: str
    output: ChatCompletionAssistantMessageParam
    tool_results: list[ChatCompletionToolMessageParam]
    messages: list[ChatCompletionMessageParam]
    tokens_in: int
    tokens_out: int
    latency_ms: int


@dataclass(frozen=True, slots=True)
class AgentResult:
    """What one call of `CallAgent.run` did, and the end state it left."""

    steps: list[AgentStep]
    messages: list[ChatCompletionMessageParam]
    final_output: str | None
    outcome: CallOutcome
    stop_reason: StopReason


type StepCallback = Callable[[AgentStep], Awaitable[None]]


def _finished(messages: Sequence[ChatCompletionMessageParam]) -> str | None:
    """Return the final answer when the conversation already ends with one."""
    turns = assistant_messages(messages[-1:])
    if turns and not function_calls(turns[0]):
        return text_of(turns[0]) or ""
    return None


class CallAgent:
    """Answers a call for the user with the mock tools, one model turn per step.

    Example:
        >>> agent = CallAgent(OpenAIChatModel(client), settings)
        >>> result = await agent.run(task, opening_messages(task, load_world().user))
    """

    def __init__(
        self, chat_model: ChatModel, settings: DemoAgentSettings, world: World | None = None
    ) -> None:
        self._chat_model = chat_model
        self._settings = settings
        self._world = world or load_world()
        self._tools = tool_specs()

    async def run(
        self,
        call: CallTask,
        messages: Sequence[ChatCompletionMessageParam],
        *,
        replacement_output: ChatCompletionAssistantMessageParam | None = None,
        model_override: str | None = None,
        step_limit: int | None = None,
        on_step: StepCallback | None = None,
    ) -> AgentResult:
        """Run from any conversation until a final answer or the step limit.

        Args:
            call: The incoming call, whose scripted caller answers `reply_to_caller`.
            messages: The conversation to continue: a task's opening messages, or a save
                point. Steps already in it count toward the limit.
            replacement_output: Use this as the next step's output instead of calling the
                model, then continue normally.
            model_override: Run the remaining steps with this model.
            step_limit: Stop after this step index, if lower than the configured maximum.
            on_step: Awaited after every step, for example to record a save point.
        """
        conversation = list(messages)
        toolbox = ToolBox(self._world, call.caller_lines)
        toolbox.replay_history(conversation)
        model = model_override or self._settings.model
        last_index = self._settings.max_steps
        if step_limit is not None:
            last_index = min(step_limit, last_index)
        steps: list[AgentStep] = []

        def result(final_output: str | None, reason: StopReason) -> AgentResult:
            return AgentResult(steps, conversation, final_output, toolbox.outcome(), reason)

        final = _finished(conversation)
        if final is not None and replacement_output is None:
            return result(final, StopReason.FINAL_ANSWER)
        next_output = replacement_output
        for index in range(len(assistant_messages(conversation)) + 1, last_index + 1):
            step = await self._step(index, conversation, toolbox, model, next_output)
            next_output = None
            conversation = step.messages
            steps.append(step)
            if on_step is not None:
                await on_step(step)
            if not function_calls(step.output):
                return result(text_of(step.output), StopReason.FINAL_ANSWER)
        return result(None, StopReason.STEP_LIMIT)

    async def _step(
        self,
        index: int,
        conversation: list[ChatCompletionMessageParam],
        toolbox: ToolBox,
        model: str,
        replacement: ChatCompletionAssistantMessageParam | None,
    ) -> AgentStep:
        started = perf_counter()
        if replacement is None:
            turn = await self._chat_model.complete(
                model=model, messages=conversation, tools=self._tools
            )
        else:
            turn = ModelTurn(message=replacement, tokens_in=0, tokens_out=0)
        tool_results: list[ChatCompletionToolMessageParam] = [
            {
                "role": "tool",
                "tool_call_id": call["id"],
                "content": toolbox.execute(call["function"]["name"], call["function"]["arguments"]),
            }
            for call in function_calls(turn.message)
        ]
        return AgentStep(
            index=index,
            model=model,
            output=turn.message,
            tool_results=tool_results,
            messages=[*conversation, turn.message, *tool_results],
            tokens_in=turn.tokens_in,
            tokens_out=turn.tokens_out,
            latency_ms=round((perf_counter() - started) * 1000),
        )
