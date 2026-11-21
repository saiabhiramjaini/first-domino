"""Column types shared by the tables: Postgres enums and Pydantic-validated JSONB."""

from enum import StrEnum
from functools import cached_property
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import Dialect
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator

from fd_shared.enums import (
    CauseCategory,
    CheckPhase,
    CheckResult,
    DiagnosisErrorCode,
    DiagnosisStatus,
    ReplayJobStatus,
    ReplayOutcome,
    RunSource,
    RunStatus,
    VerdictKind,
)


def _pg_enum(enum: type[StrEnum], name: str) -> SqlEnum:
    return SqlEnum(enum, name=name, values_callable=lambda members: [m.value for m in members])


RUN_STATUS = _pg_enum(RunStatus, "run_status")
RUN_SOURCE = _pg_enum(RunSource, "run_source")
DIAGNOSIS_STATUS = _pg_enum(DiagnosisStatus, "diagnosis_status")
VERDICT_KIND = _pg_enum(VerdictKind, "verdict_kind")
CHECK_PHASE = _pg_enum(CheckPhase, "check_phase")
CHECK_RESULT = _pg_enum(CheckResult, "check_result")
REPLAY_JOB_STATUS = _pg_enum(ReplayJobStatus, "replay_job_status")
REPLAY_OUTCOME = _pg_enum(ReplayOutcome, "replay_outcome")
CAUSE_CATEGORY = _pg_enum(CauseCategory, "cause_category")

# Stored as text (not a Postgres enum) so adding a code never needs a schema change.
DIAGNOSIS_ERROR_CODE = SqlEnum(
    DiagnosisErrorCode,
    native_enum=False,
    length=128,
    values_callable=lambda members: [m.value for m in members],
)


class PydanticJson(TypeDecorator[Any]):
    """JSONB validated through a Pydantic type on write and on read.

    Args:
        value_type: The Pydantic model, or a type such as `list[Message]`.
    """

    impl = JSONB
    cache_ok = True

    def __init__(self, value_type: Any) -> None:
        super().__init__()
        self.value_type = value_type

    @cached_property
    def _adapter(self) -> TypeAdapter[Any]:
        return TypeAdapter(self.value_type)

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        return self._adapter.dump_python(self._adapter.validate_python(value), mode="json")

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        return self._adapter.validate_python(value)
