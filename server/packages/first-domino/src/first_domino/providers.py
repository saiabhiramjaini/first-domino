"""Model API formats: turn a provider's HTTP request and response into First Domino steps,
and a step back into that provider's response (plain JSON or a server-sent event stream).

Every agent framework ends up calling a model over HTTP, so supporting the wire formats
covers any framework built on them:

- OpenAI Chat Completions (`/chat/completions`), which also covers Azure OpenAI and the
  many OpenAI-compatible APIs (Groq, Together, OpenRouter, vLLM, Ollama, LiteLLM proxies)
- OpenAI Responses (`/responses`), used by the OpenAI Agents SDK
- Anthropic Messages (`/v1/messages`)
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast

from first_domino._generated.models import Message, MessageRole, ToolCall
from first_domino.openai_format import message_from_openai
from first_domino.responses_format import items_to_messages

REPLAY_ID = "fd-replay"


@dataclass(frozen=True, slots=True)
class ModelReply:
    """What one model call produced."""

    message: Message
    model: str
    tokens_in: int = 0
    tokens_out: int = 0


class Provider(Protocol):
    """One model API's wire format."""

    name: str

    def matches(self, path: str) -> bool:
        """True when a POST to this URL path is a call to this API."""
        ...

    def request_messages(self, body: Mapping[str, Any]) -> list[Message]:
        """The conversation a request sends, system prompt included."""
        ...

    def tool_names(self, body: Mapping[str, Any]) -> list[str]:
        """The names of the function tools a request offers."""
        ...

    def parse_response(self, data: Mapping[str, Any]) -> ModelReply:
        """The model's answer in a JSON response."""
        ...

    def parse_stream(self, raw: bytes) -> ModelReply:
        """The model's answer in a streamed (server-sent events) response."""
        ...

    def build_response(self, message: Message, model: str) -> dict[str, Any]:
        """A JSON response carrying `message`, as this API would send it."""
        ...

    def build_stream(self, message: Message, model: str) -> bytes:
        """A streamed response carrying `message`, as this API would send it."""
        ...


def _events(raw: bytes) -> list[tuple[str | None, dict[str, Any]]]:
    """Parse server-sent events into (event name, JSON data) pairs, skipping `[DONE]`."""
    events: list[tuple[str | None, dict[str, Any]]] = []
    for block in raw.decode("utf-8", errors="replace").replace("\r\n", "\n").split("\n\n"):
        name: str | None = None
        data: list[str] = []
        for line in block.split("\n"):
            if line.startswith("event:"):
                name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data.append(line[len("data:") :].strip())
        payload = "\n".join(data)
        if not payload or payload == "[DONE]":
            continue
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            events.append((name, cast(dict[str, Any], parsed)))
    return events


def _sse(events: Iterable[tuple[str | None, Mapping[str, Any]]], *, done: bool = False) -> bytes:
    lines: list[str] = []
    for name, data in events:
        if name:
            lines.append(f"event: {name}")
        lines.append(f"data: {json.dumps(data)}")
        lines.append("")
    if done:
        lines += ["data: [DONE]", ""]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _text(content: object) -> str | None:
    if content is None or isinstance(content, str):
        return content
    if isinstance(content, Iterable):
        parts = [p for p in cast(Iterable[Any], content) if isinstance(p, Mapping)]
        texts = [str(p.get("text", "")) for p in parts if "text" in p]
        return "".join(texts) if texts else None
    return json.dumps(content)


def _arguments(value: object) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def _input_of(arguments: str) -> Any:
    try:
        return json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return {"input": arguments}


def _item_id(prefix: str, seed: str) -> str:
    """A Responses item id in the shape the API accepts back (`fc_...`, `msg_...`)."""
    return f"{prefix}_fdreplay{''.join(ch for ch in seed if ch.isalnum())[-40:]}"


class OpenAIChat:
    """OpenAI Chat Completions and every API compatible with it."""

    name = "openai.chat"

    def matches(self, path: str) -> bool:
        return path.endswith("/chat/completions")

    def request_messages(self, body: Mapping[str, Any]) -> list[Message]:
        return [message_from_openai(m) for m in body.get("messages") or []]

    def tool_names(self, body: Mapping[str, Any]) -> list[str]:
        tools = body.get("tools") or []
        return [t["function"]["name"] for t in tools if t.get("type") == "function"]

    def parse_response(self, data: Mapping[str, Any]) -> ModelReply:
        usage = data.get("usage") or {}
        return ModelReply(
            message=message_from_openai(data["choices"][0]["message"]),
            model=str(data.get("model", "")),
            tokens_in=int(usage.get("prompt_tokens") or 0),
            tokens_out=int(usage.get("completion_tokens") or 0),
        )

    def parse_stream(self, raw: bytes) -> ModelReply:
        text: list[str] = []
        calls: dict[int, dict[str, str]] = {}
        model, usage = "", {}
        for _, chunk in _events(raw):
            model = str(chunk.get("model") or model)
            usage = chunk.get("usage") or usage
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                if delta.get("content"):
                    text.append(str(delta["content"]))
                for part in delta.get("tool_calls") or []:
                    call = calls.setdefault(
                        int(part.get("index", 0)), {"id": "", "name": "", "arguments": ""}
                    )
                    call["id"] = part.get("id") or call["id"]
                    function = part.get("function") or {}
                    call["name"] += function.get("name") or ""
                    call["arguments"] += function.get("arguments") or ""
        message = Message(
            role=MessageRole.assistant,
            content="".join(text) or None,
            tool_calls=[ToolCall(**calls[i]) for i in sorted(calls)],
        )
        return ModelReply(
            message,
            model,
            int(usage.get("prompt_tokens") or 0),
            int(usage.get("completion_tokens") or 0),
        )

    def _assistant(self, message: Message) -> dict[str, Any]:
        out: dict[str, Any] = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            out["tool_calls"] = [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {"name": c.name, "arguments": c.arguments},
                }
                for c in message.tool_calls
            ]
        return out

    def _finish(self, message: Message) -> str:
        return "tool_calls" if message.tool_calls else "stop"

    def build_response(self, message: Message, model: str) -> dict[str, Any]:
        return {
            "id": REPLAY_ID,
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": self._assistant(message),
                    "finish_reason": self._finish(message),
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    def build_stream(self, message: Message, model: str) -> bytes:
        delta: dict[str, Any] = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            delta["tool_calls"] = [
                {
                    "index": i,
                    "id": c.id,
                    "type": "function",
                    "function": {"name": c.name, "arguments": c.arguments},
                }
                for i, c in enumerate(message.tool_calls)
            ]
        base = {"id": REPLAY_ID, "object": "chat.completion.chunk", "created": 0, "model": model}
        first = {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
        last = {
            **base,
            "choices": [{"index": 0, "delta": {}, "finish_reason": self._finish(message)}],
        }
        return _sse([(None, first), (None, last)], done=True)


class OpenAIResponses:
    """OpenAI Responses, the API the OpenAI Agents SDK uses by default."""

    name = "openai.responses"

    def matches(self, path: str) -> bool:
        return path.endswith("/responses")

    def request_messages(self, body: Mapping[str, Any]) -> list[Message]:
        messages: list[Message] = []
        if body.get("instructions"):
            messages.append(Message(role=MessageRole.system, content=str(body["instructions"])))
        given = body.get("input")
        if isinstance(given, str):
            messages.append(Message(role=MessageRole.user, content=given))
        elif isinstance(given, list):
            messages += items_to_messages(cast(Sequence[Any], given))
        return messages

    def tool_names(self, body: Mapping[str, Any]) -> list[str]:
        return [t["name"] for t in body.get("tools") or [] if t.get("type") == "function"]

    def _message_of(self, output: Sequence[Mapping[str, Any]]) -> Message:
        text: list[str] = []
        calls: list[ToolCall] = []
        for item in output:
            if item.get("type") == "message":
                text += [str(p.get("text", "")) for p in item.get("content") or [] if "text" in p]
            elif item.get("type") == "function_call":
                calls.append(
                    ToolCall(
                        id=item["call_id"], name=item["name"], arguments=item.get("arguments") or ""
                    )
                )
        return Message(role=MessageRole.assistant, content="".join(text) or None, tool_calls=calls)

    def parse_response(self, data: Mapping[str, Any]) -> ModelReply:
        usage = data.get("usage") or {}
        return ModelReply(
            self._message_of(data.get("output") or []),
            str(data.get("model", "")),
            int(usage.get("input_tokens") or 0),
            int(usage.get("output_tokens") or 0),
        )

    def parse_stream(self, raw: bytes) -> ModelReply:
        for _, event in _events(raw):
            if event.get("type") == "response.completed" and isinstance(
                event.get("response"), dict
            ):
                return self.parse_response(event["response"])
        return ModelReply(Message(role=MessageRole.assistant, content=None), "")

    def _output(self, message: Message) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        if message.content:
            output.append(
                {
                    "type": "message",
                    "id": "msg_fdreplay",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {"type": "output_text", "text": message.content, "annotations": []}
                    ],
                }
            )
        output += [
            {
                "type": "function_call",
                "id": _item_id("fc", c.id),
                "call_id": c.id,
                "name": c.name,
                "arguments": c.arguments,
                "status": "completed",
            }
            for c in message.tool_calls or []
        ]
        return output

    def build_response(self, message: Message, model: str) -> dict[str, Any]:
        return {
            "id": REPLAY_ID,
            "object": "response",
            "created_at": 0,
            "status": "completed",
            "model": model,
            "output": self._output(message),
            "parallel_tool_calls": True,
            "tool_choice": "auto",
            "tools": [],
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens_details": {"reasoning_tokens": 0},
            },
        }

    def build_stream(self, message: Message, model: str) -> bytes:
        response = self.build_response(message, model)
        created = {**response, "status": "in_progress", "output": []}
        events: list[tuple[str | None, Mapping[str, Any]]] = [
            (
                "response.created",
                {"type": "response.created", "sequence_number": 0, "response": created},
            )
        ]
        for i, item in enumerate(response["output"]):
            events.append(
                (
                    "response.output_item.done",
                    {
                        "type": "response.output_item.done",
                        "sequence_number": i + 1,
                        "output_index": i,
                        "item": item,
                    },
                )
            )
        events.append(
            (
                "response.completed",
                {
                    "type": "response.completed",
                    "sequence_number": len(events) + 1,
                    "response": response,
                },
            )
        )
        return _sse(events)


class AnthropicMessages:
    """Anthropic Messages API."""

    name = "anthropic.messages"

    def matches(self, path: str) -> bool:
        return path.endswith("/v1/messages")

    def request_messages(self, body: Mapping[str, Any]) -> list[Message]:
        messages: list[Message] = []
        system = _text(body.get("system"))
        if system:
            messages.append(Message(role=MessageRole.system, content=system))
        for turn in body.get("messages") or []:
            content = turn.get("content")
            if turn.get("role") == "assistant":
                messages.append(self._assistant_of(content))
                continue
            if isinstance(content, str):
                messages.append(Message(role=MessageRole.user, content=content))
                continue
            text: list[str] = []
            for block in content or []:
                if block.get("type") == "tool_result":
                    messages.append(
                        Message(
                            role=MessageRole.tool,
                            content=_text(block.get("content")) or "",
                            tool_call_id=block.get("tool_use_id"),
                        )
                    )
                elif block.get("type") == "text":
                    text.append(str(block.get("text", "")))
            if text:
                messages.append(Message(role=MessageRole.user, content="".join(text)))
        return messages

    def _assistant_of(self, content: object) -> Message:
        if isinstance(content, str):
            return Message(role=MessageRole.assistant, content=content)
        text: list[str] = []
        calls: list[ToolCall] = []
        for block in cast(Sequence[Mapping[str, Any]], content or []):
            if block.get("type") == "text":
                text.append(str(block.get("text", "")))
            elif block.get("type") == "tool_use":
                calls.append(
                    ToolCall(
                        id=block["id"],
                        name=block["name"],
                        arguments=_arguments(block.get("input", {})),
                    )
                )
        return Message(role=MessageRole.assistant, content="".join(text) or None, tool_calls=calls)

    def tool_names(self, body: Mapping[str, Any]) -> list[str]:
        return [str(t["name"]) for t in body.get("tools") or [] if "name" in t]

    def parse_response(self, data: Mapping[str, Any]) -> ModelReply:
        usage = data.get("usage") or {}
        return ModelReply(
            self._assistant_of(data.get("content") or []),
            str(data.get("model", "")),
            int(usage.get("input_tokens") or 0),
            int(usage.get("output_tokens") or 0),
        )

    def parse_stream(self, raw: bytes) -> ModelReply:
        blocks: dict[int, dict[str, Any]] = {}
        model, tokens_in, tokens_out = "", 0, 0
        for _, event in _events(raw):
            kind = event.get("type")
            if kind == "message_start":
                message = event.get("message") or {}
                model = str(message.get("model", ""))
                tokens_in = int((message.get("usage") or {}).get("input_tokens") or 0)
            elif kind == "content_block_start":
                block = dict(event.get("content_block") or {})
                block["_json"] = ""
                blocks[int(event.get("index", 0))] = block
            elif kind == "content_block_delta":
                block = blocks.setdefault(
                    int(event.get("index", 0)), {"type": "text", "text": "", "_json": ""}
                )
                delta = event.get("delta") or {}
                if delta.get("type") == "text_delta":
                    block["text"] = str(block.get("text", "")) + str(delta.get("text", ""))
                elif delta.get("type") == "input_json_delta":
                    block["_json"] += str(delta.get("partial_json", ""))
            elif kind == "message_delta":
                tokens_out = int((event.get("usage") or {}).get("output_tokens") or tokens_out)
        content: list[dict[str, Any]] = []
        for i in sorted(blocks):
            block = blocks[i]
            if block.get("type") == "tool_use" and block.get("_json"):
                block["input"] = _input_of(block["_json"])
            content.append({k: v for k, v in block.items() if k != "_json"})
        return ModelReply(self._assistant_of(content), model, tokens_in, tokens_out)

    def _content(self, message: Message) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = []
        if message.content:
            content.append({"type": "text", "text": message.content})
        content += [
            {"type": "tool_use", "id": c.id, "name": c.name, "input": _input_of(c.arguments)}
            for c in message.tool_calls or []
        ]
        return content

    def build_response(self, message: Message, model: str) -> dict[str, Any]:
        return {
            "id": REPLAY_ID,
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": self._content(message),
            "stop_reason": "tool_use" if message.tool_calls else "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }

    def build_stream(self, message: Message, model: str) -> bytes:
        response = self.build_response(message, model)
        start = {**response, "content": [], "stop_reason": None}
        events: list[tuple[str | None, Mapping[str, Any]]] = [
            ("message_start", {"type": "message_start", "message": start})
        ]
        for i, block in enumerate(response["content"]):
            if block["type"] == "text":
                opened = {"type": "text", "text": ""}
                delta = {"type": "text_delta", "text": block["text"]}
            else:
                opened = {"type": "tool_use", "id": block["id"], "name": block["name"], "input": {}}
                delta = {"type": "input_json_delta", "partial_json": json.dumps(block["input"])}
            events += [
                (
                    "content_block_start",
                    {"type": "content_block_start", "index": i, "content_block": opened},
                ),
                (
                    "content_block_delta",
                    {"type": "content_block_delta", "index": i, "delta": delta},
                ),
                ("content_block_stop", {"type": "content_block_stop", "index": i}),
            ]
        events += [
            (
                "message_delta",
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": response["stop_reason"], "stop_sequence": None},
                    "usage": {"output_tokens": 0},
                },
            ),
            ("message_stop", {"type": "message_stop"}),
        ]
        return _sse(events)


PROVIDERS: tuple[Provider, ...] = (OpenAIChat(), OpenAIResponses(), AnthropicMessages())


def provider_for(path: str) -> Provider | None:
    """The model API a POST to `path` calls, or None for any other request."""
    return next((provider for provider in PROVIDERS if provider.matches(path)), None)
