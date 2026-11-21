"""First Domino SDK: record agent runs and replay them on command.

Example:
    >>> import first_domino as fd
    >>> async with fd.record("call-assistant", fd.TaskInput(prompt=call_text)) as run:
    ...     ...
    ...     await run.finish(fd.RunOutcome.failed)
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
from first_domino.diagnose import diagnose, wait_for_diagnosis
from first_domino.errors import ApiRequestError, ConfigurationError, FirstDominoError
from first_domino.openai_format import message_from_openai, message_to_openai, messages_to_openai
from first_domino.recorder import RecordedRun, record
from first_domino.settings import SdkSettings
from first_domino.worker import ReplayContext, Worker
from first_domino.wrap import wrap

__all__ = [
    "ApiRequestError",
    "ConfigurationError",
    "Diagnosis",
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
    "message_from_openai",
    "message_to_openai",
    "messages_to_openai",
    "record",
    "wait_for_diagnosis",
    "wrap",
]
