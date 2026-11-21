"""First Domino SDK: record agent runs and replay them on command.

Mark the function that runs your agent, and every model call inside it is recorded,
whatever framework makes it. Then `fd.serve()` lets First Domino replay it.

Example:
    >>> import first_domino as fd
    >>> @fd.entrypoint("support-bot", check=lambda question, answer: "refund" in answer)
    ... def answer(question: str) -> str: ...
    >>> fd.serve()  # in a separate process: replays runs when First Domino asks
"""

from first_domino._generated.models import (
    Diagnosis,
    Message,
    MessageRole,
    ReplayOutcome,
    RunOutcome,
    TaskInput,
    ToolCall,
)
from first_domino.client import FirstDominoClient
from first_domino.diagnose import diagnose, wait_for_diagnosis
from first_domino.errors import ApiRequestError, ConfigurationError, FirstDominoError
from first_domino.instrument import entrypoint, init, serve, set_outcome, tool, worker
from first_domino.openai_format import message_from_openai, message_to_openai, messages_to_openai
from first_domino.recorder import RecordedRun, record, start_recording
from first_domino.settings import SdkSettings
from first_domino.worker import ReplayContext, Worker
from first_domino.wrap import wrap

__all__ = [
    "ApiRequestError",
    "ConfigurationError",
    "Diagnosis",
    "FirstDominoClient",
    "FirstDominoError",
    "Message",
    "MessageRole",
    "RecordedRun",
    "ReplayContext",
    "ReplayOutcome",
    "RunOutcome",
    "SdkSettings",
    "TaskInput",
    "ToolCall",
    "Worker",
    "diagnose",
    "entrypoint",
    "init",
    "message_from_openai",
    "message_to_openai",
    "messages_to_openai",
    "record",
    "serve",
    "set_outcome",
    "start_recording",
    "tool",
    "wait_for_diagnosis",
    "worker",
    "wrap",
]
