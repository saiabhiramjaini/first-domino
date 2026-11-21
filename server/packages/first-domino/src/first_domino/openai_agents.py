"""Record and replay agents built with the OpenAI Agents SDK.

Install with `pip install "first-domino[agents]"`. Every model call of a run goes through a
`RecordingModel`, so each turn is recorded as a step once its tool outputs appear in the
next model input. A replay resumes `Runner.run` from the saved items, returns the
replacement output in place of the first model call, and can switch the model.

Example:
    >>> from first_domino import openai_agents as fd_agents
    >>> async with fd.record("call-assistant", task) as run:
    ...     result = await fd_agents.run_recorded(agent, call_text, run)
    >>> @worker.agent("call-assistant")
    ... async def replay(ctx: fd.ReplayContext) -> RunResult:
    ...     return await fd_agents.replay(ctx, agent)
"""

import dataclasses
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from agents import (
    Agent,
    AgentOutputSchemaBase,
    Handoff,
    Model,
    ModelResponse,
    ModelSettings,
    ModelTracing,
    RunConfig,
    Runner,
    RunResult,
    Tool,
    TResponseInputItem,
    Usage,
)
from agents.items import TResponseOutputItem, TResponseStreamEvent
from agents.models.default_models import get_default_model
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)
from openai.types.responses.response_prompt_param import ResponsePromptParam

from first_domino._generated.models import Message, MessageRole
from first_domino.recorder import RecordedRun
from first_domino.responses_format import items_to_messages, messages_to_items
from first_domino.worker import ReplayContext

log = logging.getLogger("first_domino")

DEFAULT_MAX_TURNS = 20


def output_items(message: Message) -> list[TResponseOutputItem]:
    """Turn an assistant `Message` (such as a replacement output) into model output items."""
    items: list[TResponseOutputItem] = []
    if message.content:
        text = ResponseOutputText(type="output_text", text=message.content, annotations=[])
        items.append(
            ResponseOutputMessage(
                id="fd_replacement_message",
                type="message",
                role="assistant",
                status="completed",
                content=[text],
            )
        )
    items += [
        ResponseFunctionToolCall(
            type="function_call",
            id=f"fd_{call.id}",
            call_id=call.id,
            name=call.name,
            arguments=call.arguments,
            status="completed",
        )
        for call in message.tool_calls or []
    ]
    return items


@dataclass(frozen=True, slots=True)
class _PendingStep:
    before: list[Message]
    output: Message
    tokens_in: int
    tokens_out: int
    latency_ms: int


def _input_items(input: str | list[TResponseInputItem]) -> list[TResponseInputItem]:
    if isinstance(input, str):
        return [{"role": "user", "content": input}]
    return input


class RecordingModel(Model):
    """A `Model` that records each turn of the wrapped model into a run.

    When `replacement` is set, the first call returns it instead of calling the model.
    Streaming calls are passed through without recording.
    """

    def __init__(
        self,
        inner: Model,
        run: RecordedRun,
        *,
        model_name: str,
        replacement: Message | None = None,
    ) -> None:
        self._inner = inner
        self._run = run
        self._model_name = model_name
        self._replacement = replacement
        self._pending: _PendingStep | None = None
        run.add_flush_hook(self.flush)

    async def get_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: ResponsePromptParam | None,
    ) -> ModelResponse:
        """Return the next model turn, recording the previous one now that its tools ran."""
        items = _input_items(input)
        self._run.add_tool_names(str(getattr(tool, "name", "")) for tool in tools)
        await self._record_pending(items)
        started = perf_counter()
        replacement, self._replacement = self._replacement, None
        if replacement is not None:
            response = ModelResponse(
                output=output_items(replacement), usage=Usage(), response_id=None
            )
        else:
            response = await self._inner.get_response(
                system_instructions,
                input,
                model_settings,
                tools,
                output_schema,
                handoffs,
                tracing,
                previous_response_id=previous_response_id,
                conversation_id=conversation_id,
                prompt=prompt,
            )
        self._hold(items, response, round((perf_counter() - started) * 1000))
        return response

    def stream_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: ResponsePromptParam | None,
    ) -> AsyncIterator[TResponseStreamEvent]:
        """Stream from the wrapped model. Streamed turns are not recorded."""
        return self._inner.stream_response(
            system_instructions,
            input,
            model_settings,
            tools,
            output_schema,
            handoffs,
            tracing,
            previous_response_id=previous_response_id,
            conversation_id=conversation_id,
            prompt=prompt,
        )

    async def flush(self) -> None:
        """Record the last turn, which has no tool outputs after it."""
        await self._record_pending([])

    def _hold(
        self, items: list[TResponseInputItem], response: ModelResponse, latency_ms: int
    ) -> None:
        try:
            produced = items_to_messages(response.to_input_items())
            output = next(
                (m for m in produced if m.role == MessageRole.assistant),
                Message(role=MessageRole.assistant, content=None),
            )
            self._pending = _PendingStep(
                before=items_to_messages(items),
                output=output,
                tokens_in=response.usage.input_tokens,
                tokens_out=response.usage.output_tokens,
                latency_ms=latency_ms,
            )
        except Exception:
            log.debug("first_domino.agents_hold_failed", exc_info=True)

    async def _record_pending(self, next_items: list[TResponseInputItem]) -> None:
        pending, self._pending = self._pending, None
        if pending is None:
            return
        call_ids = {call.id for call in pending.output.tool_calls or []}
        tool_results = [
            m
            for m in items_to_messages(next_items)
            if m.role == MessageRole.tool and m.tool_call_id in call_ids
        ]
        await self._run.step(
            model=self._model_name,
            output=pending.output,
            tool_results=tool_results,
            messages=[*pending.before, pending.output, *tool_results],
            tokens_in=pending.tokens_in,
            tokens_out=pending.tokens_out,
            latency_ms=pending.latency_ms,
        )


def _resolve_model(
    agent: Agent[Any], run_config: RunConfig, model_override: str | None
) -> tuple[Model, str]:
    chosen = model_override or run_config.model or agent.model
    if isinstance(chosen, Model):
        return chosen, type(chosen).__name__
    name = chosen or get_default_model()
    return run_config.model_provider.get_model(name), name


async def _run(
    agent: Agent[Any],
    input: str | list[TResponseInputItem],
    model: RecordingModel,
    run_config: RunConfig,
    max_turns: int,
) -> RunResult:
    config = dataclasses.replace(run_config, model=model)
    return await Runner.run(agent, input, run_config=config, max_turns=max_turns)


async def run_recorded(
    agent: Agent[Any],
    input: str | list[TResponseInputItem],
    run: RecordedRun,
    *,
    run_config: RunConfig | None = None,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> RunResult:
    """Run an agent with `Runner.run` and record every model turn into `run`.

    The run's model (from `run_config`, else the agent) is wrapped, so it applies to every
    agent the run hands off to. Finish the run yourself after your success check.

    Example:
        >>> async with fd.record("call-assistant", task) as run:
        ...     result = await fd_agents.run_recorded(agent, call_text, run)
        ...     await run.finish(fd.RunOutcome.passed if ok(result) else fd.RunOutcome.failed)
    """
    config = run_config or RunConfig()
    inner, name = _resolve_model(agent, config, None)
    model = RecordingModel(inner, run, model_name=name)
    result = await _run(agent, input, model, config, max_turns)
    await model.flush()
    return result


async def replay(
    ctx: ReplayContext,
    agent: Agent[Any],
    *,
    run_config: RunConfig | None = None,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> RunResult:
    """Replay an agent for a First Domino replay job, recording into `ctx.run`.

    Resumes from `ctx.messages`, uses `ctx.replacement_output` as the next model turn when
    set, and runs with `ctx.model_override` when set. Your tools see only new calls: restore
    any state your tools need for the save point before calling this.

    Example:
        >>> @worker.agent("call-assistant")
        ... async def replay_call(ctx: fd.ReplayContext) -> RunResult:
        ...     return await fd_agents.replay(ctx, agent)
    """
    config = run_config or RunConfig()
    inner, name = _resolve_model(agent, config, ctx.model_override)
    model = RecordingModel(inner, ctx.run, model_name=name, replacement=ctx.replacement_output)
    result = await _run(agent, messages_to_items(ctx.messages), model, config, max_turns)
    await model.flush()
    ctx.final_output = str(result.final_output) if result.final_output is not None else None
    return result
