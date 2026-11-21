"""Convert between OpenAI Responses input items and First Domino `Message` objects.

The OpenAI Agents SDK keeps a run as a list of Responses items: messages, `function_call`
items and `function_call_output` items. First Domino keeps chat-style messages. One
assistant turn (its text and every function call it made) becomes one assistant `Message`.
Items with no chat equivalent, such as reasoning items, are dropped.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

from first_domino._generated.models import Message, MessageRole, ToolCall

if TYPE_CHECKING:
    from openai.types.responses import ResponseInputItemParam

_ROLES = {
    "user": MessageRole.user,
    "system": MessageRole.system,
    "developer": MessageRole.system,
    "assistant": MessageRole.assistant,
}


def _text(content: object) -> str | None:
    if content is None or isinstance(content, str):
        return content
    if isinstance(content, Iterable):
        parts = cast(Iterable[Mapping[str, Any]], content)
        return "".join(str(part.get("text", "")) for part in parts if "text" in part)
    return json.dumps(content)


def _add_call(messages: list[Message], call: ToolCall) -> None:
    last = messages[-1] if messages else None
    if last is not None and last.role == MessageRole.assistant:
        last.tool_calls = [*(last.tool_calls or []), call]
    else:
        messages.append(Message(role=MessageRole.assistant, content=None, tool_calls=[call]))


def items_to_messages(items: Sequence[ResponseInputItemParam]) -> list[Message]:
    """Convert Responses items into First Domino messages, one assistant message per turn.

    Example:
        >>> items_to_messages([{"role": "user", "content": "Hi"}])[0].content
        'Hi'
    """
    messages: list[Message] = []
    for item in cast(Sequence[Mapping[str, Any]], items):
        kind = item.get("type")
        if kind == "function_call":
            call = ToolCall(id=item["call_id"], name=item["name"], arguments=item["arguments"])
            _add_call(messages, call)
        elif kind == "function_call_output":
            output = _text(item.get("output"))
            messages.append(
                Message(role=MessageRole.tool, content=output, tool_call_id=item["call_id"])
            )
        elif kind in (None, "message") and item.get("role") in _ROLES:
            role = _ROLES[item["role"]]
            messages.append(Message(role=role, content=_text(item.get("content"))))
    return messages


def message_to_items(message: Message) -> list[ResponseInputItemParam]:
    """Convert one First Domino message back into Responses input items."""
    return cast("list[ResponseInputItemParam]", _items_of(message))


def _items_of(message: Message) -> list[dict[str, Any]]:
    if message.role == MessageRole.tool:
        output = message.content or ""
        return [{"type": "function_call_output", "call_id": message.tool_call_id, "output": output}]
    items: list[dict[str, Any]] = []
    if message.content or message.role != MessageRole.assistant:
        items.append({"role": message.role.value, "content": message.content or ""})
    items += [
        {"type": "function_call", "call_id": c.id, "name": c.name, "arguments": c.arguments}
        for c in message.tool_calls or []
    ]
    return items


def messages_to_items(messages: Iterable[Message]) -> list[ResponseInputItemParam]:
    """Convert First Domino messages into Responses input items, to resume a run from them.

    Example:
        >>> await Runner.run(agent, messages_to_items(ctx.messages))
    """
    return [item for message in messages for item in message_to_items(message)]
