"""Converts between the demo agent's OpenAI message params and the `fd-shared` models."""

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageFunctionToolCallParam,
    ChatCompletionMessageParam,
    ChatCompletionToolMessageParam,
)

from fd_demo_agent.agent import AgentStep
from fd_demo_agent.messages import function_calls, text_of
from fd_shared.enums import MessageRole
from fd_shared.models import Message, StepView, ToolCall


def assistant_message(param: ChatCompletionAssistantMessageParam) -> Message:
    """An assistant turn as a `fd-shared` message."""
    return Message(
        role=MessageRole.ASSISTANT,
        content=text_of(param),
        tool_calls=[
            ToolCall(
                id=call["id"],
                name=call["function"]["name"],
                arguments=call["function"]["arguments"],
            )
            for call in function_calls(param)
        ],
    )


def tool_message(param: ChatCompletionToolMessageParam) -> Message:
    """A tool result as a `fd-shared` message."""
    content = param["content"]
    text = content if isinstance(content, str) else "".join(part["text"] for part in content)
    return Message(role=MessageRole.TOOL, content=text, tool_call_id=param["tool_call_id"])


def step_view(step: AgentStep) -> StepView:
    """A demo agent step as the engine reads it."""
    return StepView(
        index=step.index,
        model=step.model,
        output=assistant_message(step.output),
        tool_results=[tool_message(result) for result in step.tool_results],
    )


def assistant_param(message: Message) -> ChatCompletionAssistantMessageParam:
    """A `fd-shared` assistant message as the demo agent's message param."""
    param: ChatCompletionAssistantMessageParam = {"role": "assistant", "content": message.content}
    calls: list[ChatCompletionMessageFunctionToolCallParam] = [
        {
            "id": call.id,
            "type": "function",
            "function": {"name": call.name, "arguments": call.arguments},
        }
        for call in message.tool_calls
    ]
    if calls:
        param["tool_calls"] = calls
    return param


def tool_param(message: Message) -> ChatCompletionToolMessageParam:
    """A `fd-shared` tool result as the demo agent's message param."""
    return {
        "role": "tool",
        "tool_call_id": message.tool_call_id or "",
        "content": message.content or "",
    }


def conversation(
    opening: list[ChatCompletionMessageParam], steps: list[StepView]
) -> list[ChatCompletionMessageParam]:
    """The conversation after `steps`: the opening messages, then each turn and its results."""
    messages = list(opening)
    for step in steps:
        messages.append(assistant_param(step.output))
        messages.extend(tool_param(result) for result in step.tool_results)
    return messages
