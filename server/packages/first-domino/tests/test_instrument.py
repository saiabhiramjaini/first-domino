"""@fd.entrypoint records any agent's model calls over HTTP, and fd.worker replays them.

A fake model API stands in for OpenAI and Anthropic: it asks for the `get_weather` tool
once, then answers. The agents below call it the ways real agents do.
"""

import json
import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import httpx2
import openai
import pytest

import first_domino as fd
from first_domino import capture
from first_domino import instrument as entrypoint_module
from first_domino._generated.models import ReplayJobStatus
from first_domino.client import FirstDominoClient
from first_domino.providers import AnthropicMessages
from first_domino.recorder import RecordedRun
from first_domino.testing import FakeApi, make_job

AGENT = "weather-bot"
QUESTION = "What is the weather in Paris?"
ANSWER = "It is sunny in Paris."


@pytest.fixture(autouse=True)
def recorder(client: FirstDominoClient) -> Iterator[None]:
    fd.init(client=client)
    yield
    entrypoint_module._CONFIG.client = None
    entrypoint_module.REGISTRY.clear()


class FakeModel:
    """A model API: calls `get_weather` until it has a result, then answers."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.fail_next = 0

    def handle(self, path: str, body: dict[str, Any]) -> tuple[int, bytes, str]:
        self.requests.append(body)
        if self.fail_next:
            self.fail_next -= 1
            return 500, b'{"error": {"message": "overloaded"}}', "application/json"
        if path.endswith("/chat/completions"):
            return self._chat(body)
        if path.endswith("/responses"):
            return self._responses(body)
        return self._anthropic(body)

    def _chat(self, body: dict[str, Any]) -> tuple[int, bytes, str]:
        answered = any(m["role"] == "tool" for m in body["messages"])
        if body.get("stream"):
            return 200, _chat_stream(answered), "text/event-stream"
        message: dict[str, Any] = {"role": "assistant", "content": ANSWER if answered else None}
        if not answered:
            message["tool_calls"] = [_chat_call()]
        data = {
            "id": "c1",
            "object": "chat.completion",
            "created": 0,
            "model": body["model"],
            "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
        }
        return 200, json.dumps(data).encode(), "application/json"

    def _responses(self, body: dict[str, Any]) -> tuple[int, bytes, str]:
        answered = any(item.get("type") == "function_call_output" for item in body["input"])
        output = fd.Message(
            role=fd.MessageRole.assistant,
            content=ANSWER if answered else None,
            tool_calls=None if answered else [_call()],
        )
        data = _RESPONSES.build_response(output, body["model"])
        data["usage"]["input_tokens"] = 5
        return 200, json.dumps(data).encode(), "application/json"

    def _anthropic(self, body: dict[str, Any]) -> tuple[int, bytes, str]:
        answered = any(
            isinstance(m["content"], list) and m["content"][0].get("type") == "tool_result"
            for m in body["messages"]
        )
        output = fd.Message(
            role=fd.MessageRole.assistant,
            content=ANSWER if answered else "Let me check.",
            tool_calls=None if answered else [_call(call_id="toolu_1")],
        )
        anthropic = AnthropicMessages()
        if body.get("stream"):
            return 200, anthropic.build_stream(output, body["model"]), "text/event-stream"
        return (
            200,
            json.dumps(anthropic.build_response(output, body["model"])).encode(),
            "application/json",
        )

    def httpx2_transport(self) -> httpx2.MockTransport:
        def handler(request: httpx2.Request) -> httpx2.Response:
            status, content, kind = self.handle(request.url.path, json.loads(request.content))
            return httpx2.Response(status, content=content, headers={"content-type": kind})

        return httpx2.MockTransport(handler)

    def httpx_transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            status, content, kind = self.handle(request.url.path, json.loads(request.content))
            return httpx.Response(status, content=content, headers={"content-type": kind})

        return httpx.MockTransport(handler)


_RESPONSES = __import__("first_domino.providers", fromlist=["OpenAIResponses"]).OpenAIResponses()


def _call(call_id: str = "call_1") -> fd.ToolCall:
    return fd.ToolCall(id=call_id, name="get_weather", arguments='{"city": "Paris"}')


def _chat_call() -> dict[str, Any]:
    arguments = '{"city": "Paris"}'
    return {
        "id": "call_1",
        "type": "function",
        "function": {"name": "get_weather", "arguments": arguments},
    }


def _chat_stream(answered: bool) -> bytes:
    """A stream split the way OpenAI splits it: text and arguments in pieces."""
    base = {"id": "c1", "object": "chat.completion.chunk", "created": 0, "model": "small"}
    if answered:
        deltas = [{"content": "It is sunny"}, {"content": " in Paris."}]
    else:
        deltas = [
            {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_weather", "arguments": ""},
                    }
                ]
            },
            {"tool_calls": [{"index": 0, "function": {"arguments": '{"city": '}}]},
            {"tool_calls": [{"index": 0, "function": {"arguments": '"Paris"}'}}]},
        ]
    chunks = [
        {**base, "choices": [{"index": 0, "delta": d, "finish_reason": None}]} for d in deltas
    ]
    chunks.append(
        {
            **base,
            "choices": [],
            "usage": {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13},
        }
    )
    return "".join(f"data: {json.dumps(c)}\n\n" for c in chunks).encode() + b"data: [DONE]\n\n"


TOOLS: list[Any] = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Weather in a city.",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
        },
    }
]

weather_calls: list[str] = []


def get_weather(city: str) -> str:
    weather_calls.append(city)
    return json.dumps({"city": city, "sky": "sunny"})


def chat_loop(client: openai.OpenAI, question: str, *, stream: bool = False) -> str:
    """A plain tool-calling loop on Chat Completions."""
    messages: list[Any] = [
        {"role": "system", "content": "Answer weather questions."},
        {"role": "user", "content": question},
    ]
    while True:
        if stream:
            reply = _streamed(client, messages)
        else:
            reply = (
                client.chat.completions.create(model="small", messages=messages, tools=TOOLS)
                .choices[0]
                .message.model_dump(exclude_none=True)
            )
        messages.append(reply)
        if not reply.get("tool_calls"):
            return reply["content"]
        for call in reply["tool_calls"]:
            city = json.loads(call["function"]["arguments"])["city"]
            messages.append(
                {"role": "tool", "tool_call_id": call["id"], "content": get_weather(city)}
            )


def _streamed(client: openai.OpenAI, messages: list[Any]) -> dict[str, Any]:
    text, calls = "", {}
    for chunk in client.chat.completions.create(
        model="small", messages=messages, tools=TOOLS, stream=True
    ):
        for choice in chunk.choices:
            text += choice.delta.content or ""
            for part in choice.delta.tool_calls or []:
                call = calls.setdefault(
                    part.index,
                    {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
                )
                call["id"] = part.id or call["id"]
                if part.function is not None:
                    call["function"]["name"] += part.function.name or ""
                    call["function"]["arguments"] += part.function.arguments or ""
    reply: dict[str, Any] = {"role": "assistant", "content": text or None}
    if calls:
        reply["tool_calls"] = list(calls.values())
    return reply


def openai_client(model: FakeModel) -> openai.OpenAI:
    http = httpx2.Client(transport=model.httpx2_transport())
    return openai.OpenAI(
        api_key="test", base_url="http://model.test/v1", http_client=http, max_retries=2
    )


def bot(
    model: FakeModel, *, stream: bool = False, check: Callable[..., bool] | None = None
) -> Callable[[str], str]:
    client = openai_client(model)

    @fd.entrypoint(AGENT, check=check or (lambda question, answer: "sunny" in answer))
    def answer(question: str) -> str:
        return chat_loop(client, question, stream=stream)

    return answer


def recorded_steps(api: FakeApi) -> list[tuple[int, str | None, list[str]]]:
    return [
        (s.index, s.output.content, [c.name for c in s.output.tool_calls or []]) for s in api.steps
    ]


@pytest.mark.parametrize("stream", [False, True])
def test_records_each_model_call_as_a_step(api: FakeApi, stream: bool) -> None:
    answer = bot(FakeModel(), stream=stream)

    assert answer(QUESTION) == ANSWER

    assert recorded_steps(api) == [(1, None, ["get_weather"]), (2, ANSWER, [])]
    first = api.steps[0]
    assert (first.tool_results or [])[0].tool_call_id == "call_1"
    assert "sunny" in ((first.tool_results or [])[0].content or "")
    assert [m.role for m in first.messages] == ["system", "user", "assistant", "tool"]
    assert first.tokens_in == (9 if stream else 11)
    start: dict[str, Any] = api.start_bodies[0]
    assert start["tool_names"] == ["get_weather"]
    assert start["task_input"]["prompt"] == QUESTION
    assert api.finished[0].status == fd.RunOutcome.passed
    assert api.finished[0].final_output == ANSWER


def test_check_decides_failed(api: FakeApi) -> None:
    bot(FakeModel(), check=lambda answer: "rain" in answer)(QUESTION)

    assert api.finished[0].status == fd.RunOutcome.failed


def test_set_outcome_wins_over_the_check(api: FakeApi) -> None:
    @fd.entrypoint(AGENT, check=lambda _: True)
    def answer(question: str) -> str:
        fd.set_outcome(passed=False, reason="no source")
        return question

    answer(QUESTION)

    assert api.finished[0].status == fd.RunOutcome.failed


def test_a_run_that_raises_is_errored_and_raises(api: FakeApi) -> None:
    @fd.entrypoint(AGENT)
    def answer(question: str) -> str:
        raise RuntimeError(question)

    with pytest.raises(RuntimeError):
        answer(QUESTION)

    assert api.finished[0].status == fd.RunOutcome.errored


def test_a_retried_model_call_keeps_its_step_number(api: FakeApi) -> None:
    model = FakeModel()
    model.fail_next = 1
    answer = bot(model)

    assert answer(QUESTION) == ANSWER

    assert [s.index for s in api.steps] == [1, 2]


def test_dark_without_an_api_key(api: FakeApi, dark_client: FirstDominoClient) -> None:
    fd.init(client=dark_client)

    assert bot(FakeModel())(QUESTION) == ANSWER

    assert api.steps == []
    assert api.start_bodies == []


def test_model_calls_outside_an_entrypoint_are_not_recorded(api: FakeApi) -> None:
    fd.init()

    assert chat_loop(openai_client(FakeModel()), QUESTION) == ANSWER

    assert api.steps == []


async def test_async_agent_on_the_responses_api(api: FakeApi) -> None:
    client = openai.AsyncOpenAI(
        api_key="test",
        base_url="http://model.test/v1",
        http_client=httpx2.AsyncClient(transport=FakeModel().httpx2_transport()),
    )
    tools: list[Any] = [
        {
            "type": "function",
            "name": "get_weather",
            "parameters": {"type": "object", "properties": {}},
        }
    ]

    @fd.entrypoint(AGENT)
    async def answer(question: str) -> str:
        items: list[Any] = [{"role": "user", "content": question}]
        while True:
            response = await client.responses.create(
                model="small", instructions="Be brief.", input=items, tools=tools
            )
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                return response.output_text
            for call in calls:
                items.append(
                    {
                        "type": "function_call",
                        "call_id": call.call_id,
                        "name": call.name,
                        "arguments": call.arguments,
                    }
                )
                items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": get_weather("Paris"),
                    }
                )

    assert await answer(QUESTION) == ANSWER

    assert recorded_steps(api) == [(1, None, ["get_weather"]), (2, ANSWER, [])]
    assert (api.steps[0].tool_results or [])[0].tool_call_id == "call_1"
    assert api.steps[0].messages[0].content == "Be brief."
    assert api.steps[0].tokens_in == 5


@pytest.mark.parametrize("stream", [False, True])
async def test_async_agent_on_the_anthropic_api(api: FakeApi, stream: bool) -> None:
    http = httpx.AsyncClient(
        transport=FakeModel().httpx_transport(), base_url="https://api.anthropic.test"
    )

    async def create(messages: list[Any]) -> dict[str, Any]:
        body = {
            "model": "claude-x",
            "system": "Be brief.",
            "messages": messages,
            "tools": [{"name": "get_weather"}],
            "max_tokens": 100,
            "stream": stream,
        }
        response = await http.post("/v1/messages", json=body)
        if not stream:
            return response.json()
        return AnthropicMessages().build_response(
            AnthropicMessages().parse_stream(response.content).message, "claude-x"
        )

    @fd.entrypoint(AGENT)
    async def answer(question: str) -> str:
        messages: list[Any] = [{"role": "user", "content": question}]
        while True:
            reply = await create(messages)
            messages.append({"role": "assistant", "content": reply["content"]})
            uses = [b for b in reply["content"] if b["type"] == "tool_use"]
            if not uses:
                return "".join(b["text"] for b in reply["content"] if b["type"] == "text")
            results = [
                {
                    "type": "tool_result",
                    "tool_use_id": u["id"],
                    "content": get_weather(u["input"]["city"]),
                }
                for u in uses
            ]
            messages.append({"role": "user", "content": results})

    assert await answer(QUESTION) == ANSWER

    assert recorded_steps(api) == [(1, "Let me check.", ["get_weather"]), (2, ANSWER, [])]
    first = api.steps[0]
    assert first.output.tool_calls is not None
    assert json.loads(first.output.tool_calls[0].arguments) == {"city": "Paris"}
    assert (first.tool_results or [])[0].tool_call_id == "toolu_1"
    assert [m.role for m in first.messages] == ["system", "user", "assistant", "tool"]


# --- replay ---------------------------------------------------------------------------------


async def test_replay_serves_recorded_steps_then_the_fix_then_the_model(
    api: FakeApi, client: FirstDominoClient
) -> None:
    model = FakeModel()
    llm = openai_client(model)
    sent: list[str] = []

    @fd.tool
    def notify(text: str) -> str:
        sent.append(text)
        return "sent"

    @fd.entrypoint(AGENT, check=lambda answer: "sunny" in answer)
    def answer(question: str) -> str:
        result = chat_loop(llm, question)
        notify(result)
        return result

    answer(QUESTION)
    run_id = next(iter(api.runs))
    recorded = list(api.steps)
    weather_calls.clear()
    model.requests.clear()
    fixed = fd.Message(role=fd.MessageRole.assistant, content="It is rainy in Paris.")
    task_input = api.runs[run_id].task_input
    api.jobs.append(
        make_job(
            agent_name=AGENT,
            run_id=run_id,
            task_input=task_input,
            from_step=1,
            replacement_output=fixed,
            model_override="big",
        )
    )

    outcome = await fd.worker(AGENT, client=client).run_once()

    assert outcome == fd.ReplayOutcome.failed
    assert model.requests == []
    assert weather_calls == ["Paris"]
    assert sent == [ANSWER, "It is rainy in Paris."]
    replay_steps = api.steps[len(recorded) :]
    assert [(s.index, s.output.content) for s in replay_steps] == [(2, "It is rainy in Paris.")]
    assert api.submitted[0].outcome == fd.ReplayOutcome.failed


async def test_replay_goes_live_after_the_recorded_part_with_the_new_model(
    api: FakeApi, client: FirstDominoClient
) -> None:
    model = FakeModel()
    llm = openai_client(model)

    @fd.entrypoint(AGENT, check=lambda answer: "sunny" in answer)
    def answer(question: str) -> str:
        return chat_loop(llm, question)

    answer(QUESTION)
    run_id = next(iter(api.runs))
    model.requests.clear()
    api.jobs.append(
        make_job(
            agent_name=AGENT,
            run_id=run_id,
            task_input=api.runs[run_id].task_input,
            from_step=1,
            model_override="big",
        )
    )

    outcome = await fd.worker(AGENT, client=client).run_once()

    assert outcome == fd.ReplayOutcome.passed
    assert [r["model"] for r in model.requests] == ["big"]
    assert [s.index for s in api.steps] == [1, 2, 2]


async def test_a_replay_nobody_needs_stops_at_its_next_model_call(
    api: FakeApi, client: FirstDominoClient
) -> None:
    model = FakeModel()
    llm = openai_client(model)
    replaying = threading.Event()

    @fd.entrypoint(AGENT, check=lambda answer: "sunny" in answer)
    def answer(question: str) -> str:
        if replaying.is_set():
            time.sleep(0.2)
        return chat_loop(llm, question)

    answer(QUESTION)
    run_id = next(iter(api.runs))
    model.requests.clear()
    job = make_job(
        agent_name=AGENT, run_id=run_id, task_input=api.runs[run_id].task_input, from_step=0
    )
    api.jobs.append(job)
    api.job_statuses[job.id] = ReplayJobStatus.expired
    replaying.set()

    outcome = await fd.worker(AGENT, client=client).run_once()

    assert outcome == fd.ReplayOutcome.errored
    assert model.requests == []
    assert api.submitted == []
    assert api.finished[-1].status == fd.RunOutcome.errored


async def test_a_stopped_replay_lets_other_requests_through(client: FirstDominoClient) -> None:
    stop = threading.Event()
    stop.set()
    session = capture.Session(RecordedRun(client, None), replay=None, stop=stop)
    capture.install()
    capture.activate(session)
    try:
        http = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(204)))
        api_call = await http.post("http://first-domino.test/v1/runs.finish", json={})
        with pytest.raises(fd.ReplayStopped):
            await http.post(
                "http://model.test/v1/chat/completions",
                json={"model": "small", "messages": [{"role": "user", "content": "hi"}]},
            )
    finally:
        capture.deactivate(session)

    assert api_call.status_code == 204


async def test_marked_tools_return_the_recorded_result_inside_the_recorded_part(
    api: FakeApi, client: FirstDominoClient
) -> None:
    model = FakeModel()
    llm = openai_client(model)
    charged: list[str] = []

    @fd.tool(name="get_weather")
    def weather(city: str) -> dict[str, str]:
        charged.append(city)
        return {"city": city, "sky": "sunny"}

    @fd.entrypoint(AGENT, check=lambda answer: "sunny" in answer)
    def answer(question: str) -> str:
        messages: list[Any] = [{"role": "user", "content": question}]
        while True:
            reply = (
                llm.chat.completions.create(model="small", messages=messages, tools=TOOLS)
                .choices[0]
                .message.model_dump(exclude_none=True)
            )
            messages.append(reply)
            if not reply.get("tool_calls"):
                return reply["content"]
            for call in reply["tool_calls"]:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(weather("Paris")),
                    }
                )

    answer(QUESTION)
    run_id = next(iter(api.runs))
    charged.clear()
    api.jobs.append(
        make_job(
            agent_name=AGENT, run_id=run_id, task_input=api.runs[run_id].task_input, from_step=1
        )
    )

    assert await fd.worker(AGENT, client=client).run_once() == fd.ReplayOutcome.passed
    assert charged == []


async def test_replay_rebuilds_typed_arguments(api: FakeApi, client: FirstDominoClient) -> None:
    from pydantic import BaseModel

    class Ticket(BaseModel):
        question: str
        priority: int

    seen: list[Ticket] = []

    @fd.entrypoint(AGENT, check=lambda ticket, answer: answer == ticket.question)
    async def answer(ticket: Ticket) -> str:
        seen.append(ticket)
        return ticket.question

    await answer(Ticket(question=QUESTION, priority=2))
    run_id = next(iter(api.runs))
    assert api.runs[run_id].task_input.metadata is not None
    api.jobs.append(
        make_job(
            agent_name=AGENT, run_id=run_id, task_input=api.runs[run_id].task_input, from_step=0
        )
    )

    assert await fd.worker(AGENT, client=client).run_once() == fd.ReplayOutcome.passed
    assert seen[-1] == Ticket(question=QUESTION, priority=2)
