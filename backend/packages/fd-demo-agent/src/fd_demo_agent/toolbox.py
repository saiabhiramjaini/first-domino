"""ToolBox: the agent's tool definitions and dispatch, bound to one run's sandbox."""

from collections.abc import Iterable
from enum import StrEnum

from openai.types.chat import ChatCompletionFunctionToolParam, ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from fd_demo_agent.messages import assistant_messages, function_calls
from fd_demo_agent.sandbox import Booking, BookingSandbox
from fd_demo_agent.tools import (
    BookAppointmentArgs,
    CheckFeeArgs,
    ListSlotsArgs,
    SearchDoctorsArgs,
    ToolError,
    ToolErrorCode,
    book_appointment,
    check_fee,
    list_slots,
    search_doctors,
)
from fd_demo_agent.world import World


class ToolName(StrEnum):
    """Names the model uses to call a tool."""

    SEARCH_DOCTORS = "search_doctors"
    LIST_SLOTS = "list_slots"
    CHECK_FEE = "check_fee"
    BOOK_APPOINTMENT = "book_appointment"


TOOL_ARGUMENTS: dict[ToolName, type[BaseModel]] = {
    ToolName.SEARCH_DOCTORS: SearchDoctorsArgs,
    ToolName.LIST_SLOTS: ListSlotsArgs,
    ToolName.CHECK_FEE: CheckFeeArgs,
    ToolName.BOOK_APPOINTMENT: BookAppointmentArgs,
}


def tool_specs() -> list[ChatCompletionFunctionToolParam]:
    """Describe every tool for the OpenAI chat completions API."""
    return [
        {
            "type": "function",
            "function": {
                "name": name.value,
                "description": args_model.__doc__ or name.value,
                "parameters": args_model.model_json_schema(),
            },
        }
        for name, args_model in TOOL_ARGUMENTS.items()
    ]


def _describe(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc']) or 'arguments'}: {item['msg']}"
        for item in error.errors()
    )


class ToolBox:
    """Runs tool calls for one agent run against the world and a fresh sandbox."""

    def __init__(self, world: World) -> None:
        self._world = world
        self._sandbox = BookingSandbox()

    @property
    def booking(self) -> Booking | None:
        """The run's appointment request, or None."""
        return self._sandbox.booking

    def execute(self, name: str, arguments: str) -> str:
        """Run one tool call and return its result as JSON text for the model.

        Never raises on bad model output: an unknown tool or bad arguments become a
        `ToolError` result the model can read and correct.
        """
        try:
            tool = ToolName(name)
        except ValueError:
            result: BaseModel = ToolError(error=ToolErrorCode.UNKNOWN_TOOL, detail=name)
        else:
            try:
                result = self._dispatch(tool, arguments)
            except ValidationError as exc:
                result = ToolError(error=ToolErrorCode.INVALID_ARGUMENTS, detail=_describe(exc))
        return result.model_dump_json()

    def replay_history(self, messages: Iterable[ChatCompletionMessageParam]) -> None:
        """Rebuild the sandbox from the tool calls already in a conversation.

        Tools are deterministic, so re-running the recorded calls recreates the exact
        state a run had at that save point.
        """
        for message in assistant_messages(messages):
            for call in function_calls(message):
                self.execute(call["function"]["name"], call["function"]["arguments"])

    def _dispatch(self, tool: ToolName, arguments: str) -> BaseModel:
        world = self._world
        match tool:
            case ToolName.SEARCH_DOCTORS:
                return search_doctors(world, SearchDoctorsArgs.model_validate_json(arguments))
            case ToolName.LIST_SLOTS:
                return list_slots(world, ListSlotsArgs.model_validate_json(arguments))
            case ToolName.CHECK_FEE:
                return check_fee(world, CheckFeeArgs.model_validate_json(arguments))
            case ToolName.BOOK_APPOINTMENT:
                args = BookAppointmentArgs.model_validate_json(arguments)
                return book_appointment(world, self._sandbox, args)
