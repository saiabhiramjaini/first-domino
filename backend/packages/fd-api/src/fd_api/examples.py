"""Fixed example data that every handler answers with until its real handler lands.

EXAMPLE DATA (contract v1): one project, one failed clinic booking run with a diagnosed
wrong-date step, its checks and cause, a benchmark and a replay job. Delete each piece as
the real handler for its resource replaces it.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fd_api.models.api_keys import ApiKey
from fd_api.models.benchmarks import Benchmark, BenchmarkScore
from fd_api.models.causes import Cause
from fd_api.models.checks import Check
from fd_api.models.diagnoses import Diagnosis
from fd_api.models.projects import Project
from fd_api.models.replay_jobs import ReplayJob
from fd_api.models.runs import Run
from fd_api.models.steps import Step, StepSnapshot
from fd_shared.enums import (
    BenchmarkMethod,
    CauseCategory,
    CheckPhase,
    CheckResult,
    DiagnosisStatus,
    MessageRole,
    ReplayJobStatus,
    RunSource,
    RunStatus,
    VerdictKind,
)
from fd_shared.models import Explanation, Message, TaskInput, ToolCall

PROJECT_ID = UUID("00000000-0000-4000-8000-000000000001")
USER_ID = UUID("00000000-0000-4000-8000-000000000002")
API_KEY_ID = UUID("00000000-0000-4000-8000-000000000003")
RUN_ID = UUID("00000000-0000-4000-8000-000000000010")
DIAGNOSIS_ID = UUID("00000000-0000-4000-8000-000000000020")
CAUSE_ID = UUID("00000000-0000-4000-8000-000000000030")
BENCHMARK_ID = UUID("00000000-0000-4000-8000-000000000040")
REPLAY_JOB_ID = UUID("00000000-0000-4000-8000-000000000050")
STEP_IDS = [UUID(f"00000000-0000-4000-8000-00000000011{index}") for index in range(1, 5)]
CHECK_IDS = [UUID(f"00000000-0000-4000-8000-00000000021{index}") for index in range(4)]

API_KEY_SECRET = "fd_live_example_secret_shown_once"
AGENT_NAME = "clinic-booker"
MODEL = "example-small-model"
T0 = datetime(2026, 11, 21, 10, 0, tzinfo=UTC)


def _at(seconds: int) -> datetime:
    return T0 + timedelta(seconds=seconds)


PROJECT = Project(
    id=PROJECT_ID,
    name="Example project",
    slack_webhook_set=False,
    created_at=T0,
    updated_at=T0,
)

API_KEY = ApiKey(
    id=API_KEY_ID,
    name="local",
    prefix=API_KEY_SECRET[:12],
    created_at=T0,
    created_by_id=USER_ID,
    last_used_at=_at(60),
    revoked_at=None,
    revoked_by_id=None,
)

TASK_INPUT = TaskInput(
    prompt="Book Dr. Mehta at Sunrise Clinic, Pune, for next Tuesday morning.",
    metadata={"task_id": "t1"},
)

SYSTEM_MESSAGE = Message(
    role=MessageRole.SYSTEM,
    content="You book doctor appointments. Today is Saturday 21 November 2026.",
)
USER_MESSAGE = Message(role=MessageRole.USER, content=TASK_INPUT.prompt)


def _tool_step(index: int, name: str, arguments: str, result: str) -> tuple[Message, Message]:
    call_id = f"call_{index}"
    output = Message(
        role=MessageRole.ASSISTANT,
        content=None,
        tool_calls=[ToolCall(id=call_id, name=name, arguments=arguments)],
    )
    tool_result = Message(role=MessageRole.TOOL, content=result, tool_call_id=call_id)
    return output, tool_result


_STEP_TURNS = [
    _tool_step(
        1,
        "search_doctors",
        '{"name": "Mehta", "clinic": "Sunrise Clinic", "city": "Pune"}',
        '[{"doctor_id": "d7", "name": "Dr. Anil Mehta"}]',
    ),
    _tool_step(
        2,
        "get_slots",
        '{"doctor_id": "d7", "date": "2026-11-23"}',
        '[{"slot_id": "s3", "time": "09:30"}]',
    ),
    _tool_step(3, "book_slot", '{"slot_id": "s3"}', '{"booking_id": "b42"}'),
]
_FINAL_OUTPUT = Message(
    role=MessageRole.ASSISTANT,
    content="Booked Dr. Mehta at Sunrise Clinic for Monday 23 November at 09:30.",
)

STEPS = [
    Step(
        id=STEP_IDS[index - 1],
        run_id=RUN_ID,
        index=index,
        model=MODEL,
        output=output,
        tool_results=[tool_result],
        tokens_in=900 + 150 * index,
        tokens_out=40,
        latency_ms=850,
        created_at=_at(index * 2),
    )
    for index, (output, tool_result) in enumerate(_STEP_TURNS, start=1)
] + [
    Step(
        id=STEP_IDS[3],
        run_id=RUN_ID,
        index=4,
        model=MODEL,
        output=_FINAL_OUTPUT,
        tool_results=[],
        tokens_in=1500,
        tokens_out=30,
        latency_ms=700,
        created_at=_at(8),
    )
]

SNAPSHOT = StepSnapshot(
    step_id=STEP_IDS[0],
    messages=[SYSTEM_MESSAGE, USER_MESSAGE, *_STEP_TURNS[0]],
)

RUN = Run(
    id=RUN_ID,
    agent_name=AGENT_NAME,
    source=RunSource.RECORDED,
    parent_run_id=None,
    replay_job_id=None,
    replay_from_step=None,
    task_input=TASK_INPUT,
    status=RunStatus.FAILED,
    step_count=len(STEPS),
    final_output=_FINAL_OUTPUT.content,
    latest_diagnosis_id=DIAGNOSIS_ID,
    created_by_id=API_KEY_ID,
    started_at=T0,
    finished_at=_at(9),
)

EXPLANATION = Explanation(
    title="Looked up slots for the wrong day",
    summary=(
        "Asked for slots on Monday 23 November instead of Tuesday 24 November, "
        "so every later step booked the wrong day."
    ),
    suggested_fix="Resolve relative dates against today's date before calling get_slots.",
    category=CauseCategory.WRONG_DATE,
)

FIXED_OUTPUT, _ = _tool_step(2, "get_slots", '{"doctor_id": "d7", "date": "2026-11-24"}', "unused")

DIAGNOSIS = Diagnosis(
    id=DIAGNOSIS_ID,
    run_id=RUN_ID,
    status=DiagnosisStatus.DONE,
    verdict_kind=VerdictKind.STEP_VERIFIED,
    first_domino_step=2,
    search_low=2,
    search_high=2,
    verify_passes=4,
    verify_samples=5,
    fixed_output=FIXED_OUTPUT,
    explanation=EXPLANATION,
    cause_id=CAUSE_ID,
    check_count=len(CHECK_IDS),
    replay_count=14,
    cost_usd=0.0421,
    error_code=None,
    created_by_id=None,
    created_at=_at(10),
    finished_at=_at(95),
)

_CHECK_PLAN = [
    (CheckPhase.PRECHECK, 0, 3, 3, CheckResult.CAN_SUCCEED),
    (CheckPhase.BISECT, 2, 3, 0, CheckResult.DOOMED),
    (CheckPhase.BISECT, 1, 3, 2, CheckResult.CAN_SUCCEED),
    (CheckPhase.VERIFY, 2, 5, 4, CheckResult.CAN_SUCCEED),
]

CHECKS = [
    Check(
        id=CHECK_IDS[index],
        diagnosis_id=DIAGNOSIS_ID,
        index=index,
        phase=phase,
        save_point=save_point,
        samples=samples,
        passes=passes,
        result=result,
        created_at=_at(10 + 15 * index),
        finished_at=_at(24 + 15 * index),
    )
    for index, (phase, save_point, samples, passes, result) in enumerate(_CHECK_PLAN)
]

CAUSE = Cause(
    id=CAUSE_ID,
    title=EXPLANATION.title,
    category=EXPLANATION.category,
    step_name="get_slots",
    summary=EXPLANATION.summary,
    suggested_fix=EXPLANATION.suggested_fix,
    run_count=1,
    verified_count=1,
    first_seen_at=_at(95),
    last_seen_at=_at(95),
)

BENCHMARK = Benchmark(
    id=BENCHMARK_ID,
    created_at=_at(3600),
    scores=[
        BenchmarkScore(
            method=BenchmarkMethod.FIRST_DOMINO,
            runs_scored=40,
            exact_accuracy=0.85,
            within_one_accuracy=0.95,
            verified_rate=0.8,
            mean_cost_usd=0.04,
            mean_seconds=90.0,
        ),
        BenchmarkScore(
            method=BenchmarkMethod.READ_TRACE_JUDGE,
            runs_scored=40,
            exact_accuracy=0.55,
            within_one_accuracy=0.7,
            verified_rate=None,
            mean_cost_usd=0.01,
            mean_seconds=6.0,
        ),
    ],
)

REPLAY_JOB = ReplayJob(
    id=REPLAY_JOB_ID,
    run_id=RUN_ID,
    agent_name=AGENT_NAME,
    task_input=TASK_INPUT,
    from_step=1,
    messages=SNAPSHOT.messages,
    replacement_output=None,
    model_override=None,
    status=ReplayJobStatus.LEASED,
    lease_expires_at=_at(200),
    attempt=1,
)
