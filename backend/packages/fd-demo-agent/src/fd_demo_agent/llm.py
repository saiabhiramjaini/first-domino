"""The chat model port the agent calls, and its OpenAI implementation."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageFunctionToolCallParam,
    ChatCompletionMessageParam,
    ChatCompletionToolUnionParam,
)

from fd_demo_agent.settings import DemoAgentSettings


@dataclass(frozen=True, slots=True)
class ModelTurn:
    """One assistant message and the tokens it cost."""

    message: ChatCompletionAssistantMessageParam
    tokens_in: int
    tokens_out: int


class ChatModel(Protocol):
    """Anything that can produce the next assistant turn of a conversation."""

    async def complete(
        self,
        *,
        model: str,
        messages: Sequence[ChatCompletionMessageParam],
        tools: Sequence[ChatCompletionToolUnionParam],
    ) -> ModelTurn:
        """Return the model's next turn for this conversation."""
        ...


def _as_param(message: ChatCompletionMessage) -> ChatCompletionAssistantMessageParam:
    param: ChatCompletionAssistantMessageParam = {"role": "assistant", "content": message.content}
    calls: list[ChatCompletionMessageFunctionToolCallParam] = [
        {
            "id": call.id,
            "type": "function",
            "function": {"name": call.function.name, "arguments": call.function.arguments},
        }
        for call in message.tool_calls or []
        if isinstance(call, ChatCompletionMessageFunctionToolCall)
    ]
    if calls:
        param["tool_calls"] = calls
    return param


class OpenAIChatModel:
    """ChatModel over the OpenAI chat completions API, one tool call per turn."""

    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    async def complete(
        self,
        *,
        model: str,
        messages: Sequence[ChatCompletionMessageParam],
        tools: Sequence[ChatCompletionToolUnionParam],
    ) -> ModelTurn:
        """Call the model once and return its message as a request param."""
        response = await self._client.chat.completions.create(
            model=model, messages=messages, tools=tools, parallel_tool_calls=False
        )
        usage = response.usage
        return ModelTurn(
            message=_as_param(response.choices[0].message),
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
        )


def openai_client(settings: DemoAgentSettings) -> AsyncOpenAI:
    """Build the process's one OpenAI client from settings.

    Raises:
        ValueError: `OPENAI_API_KEY` is not set.
    """
    if settings.openai_api_key is None:
        msg = "OPENAI_API_KEY is not set; add it to backend/.env"
        raise ValueError(msg)
    return AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
