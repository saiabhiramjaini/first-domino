"""The only OpenAI client in the backend: structured calls with retry, salvage and degrade."""

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from fd_engine.errors import EngineError
from fd_engine.settings import EngineSettings

_MILLION = 1_000_000


class LlmNotConfiguredError(EngineError):
    """The engine needs a model call but `OPENAI_API_KEY` is not set."""

    code = "llm_not_configured"


class LlmCallError(EngineError):
    """One model call failed before it returned any text."""

    code = "llm_call_failed"
    retryable = True


class ReplyQuality(StrEnum):
    """How much of a structured reply came from the model."""

    PARSED = "parsed"
    SALVAGED = "salvaged"
    DEGRADED = "degraded"


class LlmUsage(BaseModel):
    """Tokens and cost of one or more model calls."""

    model_config = ConfigDict(frozen=True)

    tokens_in: int = Field(default=0, ge=0)
    tokens_out: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0)

    def plus(self, other: "LlmUsage") -> "LlmUsage":
        """Return the sum of both usages."""
        return LlmUsage(
            tokens_in=self.tokens_in + other.tokens_in,
            tokens_out=self.tokens_out + other.tokens_out,
            cost_usd=self.cost_usd + other.cost_usd,
        )


@dataclass(frozen=True, slots=True)
class RawCompletion:
    """The text and token counts of one model call."""

    content: str | None
    tokens_in: int
    tokens_out: int


@dataclass(frozen=True, slots=True)
class LlmReply[T: BaseModel]:
    """A structured reply. `value` is the fallback when `quality` is `degraded`."""

    value: T
    quality: ReplyQuality
    usage: LlmUsage


class LlmTransport(Protocol):
    """Sends one prompt and returns the model's raw JSON text."""

    async def complete(
        self, *, system: str, user: str, schema: type[BaseModel], timeout_seconds: float
    ) -> RawCompletion:
        """Return the reply text, or raise `LlmCallError` when no reply came back."""
        ...


class OpenAiTransport:
    """Chat completions with a JSON schema response format, on one shared client."""

    def __init__(self, settings: EngineSettings, client: AsyncOpenAI | None = None) -> None:
        if client is None:
            if settings.openai_api_key is None:
                raise LlmNotConfiguredError
            client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        self._client = client
        self._model = settings.strong_model

    async def complete(
        self, *, system: str, user: str, schema: type[BaseModel], timeout_seconds: float
    ) -> RawCompletion:
        """Ask for JSON matching `schema` and return the text unparsed."""
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
                },
                timeout=timeout_seconds,
            )
        except OpenAIError as error:
            raise LlmCallError from error
        usage = completion.usage
        return RawCompletion(
            content=completion.choices[0].message.content if completion.choices else None,
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
        )


class Llm:
    """Structured model calls that never raise on a bad reply.

    Each call retries `llm_parse_retries` times, then salvages the valid fields of the last
    reply over the caller's fallback, then degrades to the fallback itself.
    """

    def __init__(self, settings: EngineSettings, transport: LlmTransport | None = None) -> None:
        self._settings = settings
        self._transport = transport or OpenAiTransport(settings)

    async def structured[T: BaseModel](
        self, *, system: str, user: str, schema: type[T], fallback: T
    ) -> LlmReply[T]:
        """Return the model's reply parsed into `schema`, salvaged, or `fallback`."""
        usage = LlmUsage()
        last_text: str | None = None
        for _ in range(1 + self._settings.llm_parse_retries):
            try:
                raw = await self._transport.complete(
                    system=system,
                    user=user,
                    schema=schema,
                    timeout_seconds=self._settings.llm_timeout_seconds,
                )
            except LlmCallError:
                continue
            usage = usage.plus(self._usage(raw))
            last_text = raw.content
            parsed = _parse(schema, raw.content)
            if parsed is not None:
                return LlmReply(value=parsed, quality=ReplyQuality.PARSED, usage=usage)
        salvaged = salvage(schema, last_text, fallback)
        if salvaged is not None:
            return LlmReply(value=salvaged, quality=ReplyQuality.SALVAGED, usage=usage)
        return LlmReply(value=fallback, quality=ReplyQuality.DEGRADED, usage=usage)

    def _usage(self, raw: RawCompletion) -> LlmUsage:
        cost = (
            raw.tokens_in * self._settings.llm_input_usd_per_million_tokens
            + raw.tokens_out * self._settings.llm_output_usd_per_million_tokens
        ) / _MILLION
        return LlmUsage(tokens_in=raw.tokens_in, tokens_out=raw.tokens_out, cost_usd=cost)


def _parse[T: BaseModel](schema: type[T], text: str | None) -> T | None:
    if text is None:
        return None
    try:
        return schema.model_validate_json(text)
    except ValidationError:
        return None


def _json_object(text: str | None) -> dict[str, object] | None:
    """The outermost JSON object in `text`, ignoring prose or fences around it."""
    if text is None:
        return None
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def salvage[T: BaseModel](schema: type[T], text: str | None, fallback: T) -> T | None:
    """Keep each field of the reply that is valid on its own, over `fallback`.

    Returns None when no field of the reply was usable.
    """
    data = _json_object(text)
    if data is None:
        return None
    merged = fallback.model_dump()
    kept = 0
    for name, value in data.items():
        if name not in schema.model_fields:
            continue
        candidate = {**merged, name: value}
        try:
            schema.model_validate(candidate)
        except ValidationError:
            continue
        merged = candidate
        kept += 1
    return schema.model_validate(merged) if kept else None
