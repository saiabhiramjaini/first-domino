"""Convert between OpenAI chat message params and First Domino `Message` objects.

Works on plain dicts, so it needs no `openai` install at run time.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any, cast

from first_domino._generated.models import Message, MessageRole, ToolCall

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam


def _text(content: object) -> str | None:
    if content is None or isinstance(content, str):
        return content
    if isinstance(content, Iterable):
        parts = [
            str(part.get("text", ""))
            for part in cast(Iterable[Mapping[str, Any]], content)
            if part.get("type") == "text"
        ]
        return "".join(parts)
    return str(content)


def message_from_openai(param: Mapping[str, Any]) -> Message:
    """Convert one OpenAI chat message param into a First Domino `Message`.

    Example:
        >>> message_from_openai({"role": "user", "content": "Hi"}).content
        'Hi'
    """
    role = MessageRole("system" if param["role"] == "developer" else param["role"])
    calls = [
        ToolCall(
            id=call["id"], name=call["function"]["name"], arguments=call["function"]["arguments"]
        )
        for call in param.get("tool_calls") or []
        if call.get("type", "function") == "function"
    ]
    return Message(
        role=role,
        content=_text(param.get("content")),
        tool_calls=calls,
        tool_call_id=param.get("tool_call_id"),
    )


def message_to_openai(message: Message) -> ChatCompletionMessageParam:
    """Convert a First Domino `Message` back into an OpenAI chat message param.

    Example:
        >>> message_to_openai(job.replacement_output)
        {'role': 'assistant', 'content': None, 'tool_calls': [...]}
    """
    param: dict[str, Any] = {"role": message.role.value, "content": message.content}
    if message.tool_calls:
        param["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.arguments},
            }
            for call in message.tool_calls
        ]
    if message.role == MessageRole.tool:
        param["tool_call_id"] = message.tool_call_id or ""
    return cast("ChatCompletionMessageParam", param)


def messages_to_openai(messages: Iterable[Message]) -> list[ChatCompletionMessageParam]:
    """Convert a list of First Domino messages into OpenAI chat message params.

    Example:
        >>> messages_to_openai(ctx.messages)
    """
    return [message_to_openai(message) for message in messages]
