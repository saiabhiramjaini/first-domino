"""ToolBox: the agent's tool definitions and dispatch, bound to one call's sandbox."""

from collections.abc import Iterable, Sequence
from enum import StrEnum

from openai.types.chat import ChatCompletionFunctionToolParam, ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from fd_demo_agent import tools
from fd_demo_agent.messages import assistant_messages, function_calls
from fd_demo_agent.sandbox import CallOutcome, CallSandbox
from fd_demo_agent.world import World


class ToolName(StrEnum):
    """Names the model uses to call a tool."""

    LOOKUP_CONTACT = "lookup_contact"
    SEARCH_MEMORY = "search_memory"
    CHECK_CALENDAR = "check_calendar"
    REPLY_TO_CALLER = "reply_to_caller"
    ADD_CALENDAR_EVENT = "add_calendar_event"
    MOVE_CALENDAR_EVENT = "move_calendar_event"
    SET_REMINDER = "set_reminder"
    SCHEDULE_CALLBACK = "schedule_callback"
    BLOCK_CALLER = "block_caller"
    SEND_CALL_SUMMARY = "send_call_summary"
    END_CALL = "end_call"


TOOL_ARGUMENTS: dict[ToolName, type[BaseModel]] = {
    ToolName.LOOKUP_CONTACT: tools.LookupContactArgs,
    ToolName.SEARCH_MEMORY: tools.SearchMemoryArgs,
    ToolName.CHECK_CALENDAR: tools.CheckCalendarArgs,
    ToolName.REPLY_TO_CALLER: tools.ReplyToCallerArgs,
    ToolName.ADD_CALENDAR_EVENT: tools.AddCalendarEventArgs,
    ToolName.MOVE_CALENDAR_EVENT: tools.MoveCalendarEventArgs,
    ToolName.SET_REMINDER: tools.SetReminderArgs,
    ToolName.SCHEDULE_CALLBACK: tools.ScheduleCallbackArgs,
    ToolName.BLOCK_CALLER: tools.BlockCallerArgs,
    ToolName.SEND_CALL_SUMMARY: tools.SendCallSummaryArgs,
    ToolName.END_CALL: tools.EndCallArgs,
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
    """Runs tool calls for one call against the world and a fresh sandbox."""

    def __init__(self, world: World, caller_lines: Sequence[str]) -> None:
        self._world = world
        self._sandbox = CallSandbox(world, caller_lines)

    def outcome(self) -> CallOutcome:
        """Everything this run has changed so far."""
        return self._sandbox.outcome()

    def execute(self, name: str, arguments: str) -> str:
        """Run one tool call and return its result as JSON text for the model.

        Never raises on bad model output: an unknown tool or bad arguments become a
        `ToolError` result the model can read and correct.
        """
        try:
            tool = ToolName(name)
        except ValueError:
            result: BaseModel = tools.ToolError(error=tools.ToolErrorCode.UNKNOWN_TOOL, detail=name)
        else:
            try:
                args = TOOL_ARGUMENTS[tool].model_validate_json(arguments or "{}")
            except ValidationError as exc:
                code = tools.ToolErrorCode.INVALID_ARGUMENTS
                result = tools.ToolError(error=code, detail=_describe(exc))
            else:
                result = self._dispatch(args)
        return result.model_dump_json()

    def replay_history(self, messages: Iterable[ChatCompletionMessageParam]) -> None:
        """Rebuild the sandbox from the tool calls already in a conversation.

        Tools and the caller script are deterministic, so re-running the recorded calls
        recreates the exact state a run had at that save point.
        """
        for message in assistant_messages(messages):
            for call in function_calls(message):
                self.execute(call["function"]["name"], call["function"]["arguments"])

    def _dispatch(self, args: BaseModel) -> BaseModel:  # noqa: C901 one branch per tool is the clearest form
        world, sandbox = self._world, self._sandbox
        match args:
            case tools.LookupContactArgs():
                return tools.lookup_contact(world, args)
            case tools.SearchMemoryArgs():
                return tools.search_memory(world, args)
            case tools.CheckCalendarArgs():
                return tools.check_calendar(sandbox, args)
            case tools.ReplyToCallerArgs():
                return tools.reply_to_caller(sandbox, args)
            case tools.AddCalendarEventArgs():
                return tools.add_calendar_event(world, sandbox, args)
            case tools.MoveCalendarEventArgs():
                return tools.move_calendar_event(world, sandbox, args)
            case tools.SetReminderArgs():
                return tools.set_reminder(sandbox, args)
            case tools.ScheduleCallbackArgs():
                return tools.schedule_callback(world, sandbox, args)
            case tools.BlockCallerArgs():
                return tools.block_caller(sandbox, args)
            case tools.SendCallSummaryArgs():
                return tools.send_call_summary(sandbox, args)
            case tools.EndCallArgs():
                return tools.end_call(sandbox)
            case _:
                msg = f"no handler for {type(args).__name__}"
                raise TypeError(msg)
