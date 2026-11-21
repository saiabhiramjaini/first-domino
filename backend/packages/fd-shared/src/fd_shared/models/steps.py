"""Chat messages and tool calls, in the shape the OpenAI chat format uses."""

from pydantic import BaseModel, ConfigDict, Field

from fd_shared.enums import MessageRole


class ToolCall(BaseModel):
    """One tool call the model asked for in an assistant message."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Tool call id, minted by the model provider.")
    name: str = Field(description="Name of the tool the model called.")
    arguments: str = Field(description="Arguments as JSON text, exactly as the provider returned.")


class Message(BaseModel):
    """One chat message: a system prompt, a user turn, a model turn or a tool result."""

    model_config = ConfigDict(frozen=True)

    role: MessageRole
    content: str | None = Field(description="Text of the message, or null when it has none.")
    tool_calls: list[ToolCall] = Field(
        default_factory=list, description="Tool calls in an assistant message. Empty when none."
    )
    tool_call_id: str | None = Field(
        default=None, description="On a `tool` message, the id of the call it answers."
    )


class StepView(BaseModel):
    """One recorded step as the engine reads it."""

    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=1)
    model: str
    output: Message
    tool_results: list[Message]
