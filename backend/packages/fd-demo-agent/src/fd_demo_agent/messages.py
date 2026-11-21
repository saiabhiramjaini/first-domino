"""Helpers over OpenAI chat message params, the agent's native conversation format."""

from collections.abc import Iterable

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageFunctionToolCallParam,
    ChatCompletionMessageParam,
)


def function_calls(
    message: ChatCompletionAssistantMessageParam,
) -> list[ChatCompletionMessageFunctionToolCallParam]:
    """Return the function tool calls of an assistant message, in order."""
    return [call for call in message.get("tool_calls", []) if call["type"] == "function"]


def assistant_messages(
    messages: Iterable[ChatCompletionMessageParam],
) -> list[ChatCompletionAssistantMessageParam]:
    """Return the assistant turns of a conversation; one per completed step."""
    return [message for message in messages if message["role"] == "assistant"]


def text_of(message: ChatCompletionAssistantMessageParam) -> str | None:
    """Return the plain-text content of an assistant message, or None when it has none."""
    content = message.get("content")
    if content is None or isinstance(content, str):
        return content
    parts = [part["text"] for part in content if part["type"] == "text"]
    return "".join(parts) or None
