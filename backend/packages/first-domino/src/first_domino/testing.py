"""An in-memory First Domino API for tests, so a worker or recorder runs with no network.

Example:
    >>> api = FakeApi()
    >>> api.jobs.append(make_job(agent_name="call-assistant"))
    >>> worker = fd.Worker(agent_names=["call-assistant"], client=fake_client(api))
    >>> await worker.run_once()
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
from pydantic import SecretStr

from first_domino._generated.models import (
    ApiError,
    ApiErrorCode,
    CreateDiagnosisRequest,
    Diagnosis,
    DiagnosisStatus,
    FinishRunRequest,
    LeaseReplayJobRequest,
    Message,
    MessageRole,
    RecordStepRequest,
    ReplayJob,
    ReplayJobStatus,
    Run,
    RunSource,
    RunStatus,
    StartRunRequest,
    Step,
    SubmitReplayResultRequest,
    TaskInput,
)
from first_domino.client import FirstDominoClient
from first_domino.settings import SdkSettings

NOW = datetime(2026, 11, 21, 5, 30, tzinfo=UTC)
KEY_ID = uuid4()


def make_job(**changes: object) -> ReplayJob:
    """Return a leased replay job for `call-assistant`, with any fields changed."""
    job = ReplayJob(
        id=uuid4(),
        run_id=uuid4(),
        agent_name="call-assistant",
        task_input=TaskInput(prompt="Incoming call", metadata={"task_id": "t01"}),
        from_step=2,
        messages=[Message(role=MessageRole.user, content="Incoming call")],
        replacement_output=None,
        model_override=None,
        status=ReplayJobStatus.leased,
        lease_expires_at=NOW,
        attempt=1,
    )
    return job.model_copy(update=changes)


class FakeApi:
    """Records every request and answers like the real API would.

    Put jobs in `jobs` for the worker to lease, and map an action such as
    `"steps.record"` to an HTTP status in `fail_paths` to make it fail.
    """

    def __init__(self) -> None:
        self.runs: dict[UUID, Run] = {}
        self.steps: list[RecordStepRequest] = []
        self.finished: list[FinishRunRequest] = []
        self.jobs: list[ReplayJob] = []
        self.submitted: list[SubmitReplayResultRequest] = []
        self.diagnosis_statuses: list[DiagnosisStatus] = [DiagnosisStatus.queued]
        self.fail_paths: dict[str, int] = {}
        self.auth_headers: list[str | None] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.auth_headers.append(request.headers.get("Authorization"))
        action = request.url.path.removeprefix("/v1/")
        if action in self.fail_paths:
            status = self.fail_paths[action]
            body = ApiError(code=ApiErrorCode.conflict, title="Conflict", detail="busy")
            return httpx.Response(status, content=body.model_dump_json())
        route = self._routes()[action]
        return httpx.Response(200, json=json.loads(route(request)))

    def _routes(self) -> dict[str, Callable[[httpx.Request], str]]:
        return {
            "runs.start": self._start,
            "steps.record": self._record,
            "runs.finish": self._finish,
            "replay-jobs.lease": self._lease,
            "replay-jobs.submit": self._submit,
            "diagnoses.create": self._diagnosis,
            "diagnoses.get": self._diagnosis,
        }

    def _start(self, request: httpx.Request) -> str:
        body = StartRunRequest.model_validate_json(request.content)
        run = Run(
            id=uuid4(),
            agent_name=body.agent_name,
            source=RunSource.replay if body.replay_job_id else RunSource.recorded,
            parent_run_id=None,
            replay_job_id=body.replay_job_id,
            replay_from_step=None,
            task_input=body.task_input,
            tool_names=body.tool_names or [],
            status=RunStatus.running,
            step_count=0,
            final_output=None,
            latest_diagnosis_id=None,
            created_by_id=KEY_ID,
            started_at=NOW,
            finished_at=None,
        )
        self.runs[run.id] = run
        return json.dumps({"run": json.loads(run.model_dump_json())})

    def _record(self, request: httpx.Request) -> str:
        body = RecordStepRequest.model_validate_json(request.content)
        self.steps.append(body)
        step = Step(
            id=uuid4(),
            run_id=body.run_id,
            index=body.index,
            model=body.model,
            output=body.output,
            tool_results=body.tool_results or [],
            tokens_in=body.tokens_in,
            tokens_out=body.tokens_out,
            latency_ms=body.latency_ms,
            created_at=NOW,
        )
        return json.dumps({"step": json.loads(step.model_dump_json())})

    def _finish(self, request: httpx.Request) -> str:
        body = FinishRunRequest.model_validate_json(request.content)
        self.finished.append(body)
        run = self.runs[body.run_id].model_copy(update={"final_output": body.final_output})
        return json.dumps({"run": json.loads(run.model_dump_json())})

    def _lease(self, request: httpx.Request) -> str:
        body = LeaseReplayJobRequest.model_validate_json(request.content)
        job = next((j for j in self.jobs if j.agent_name in body.agent_names), None)
        if job is not None:
            self.jobs.remove(job)
        payload = json.loads(job.model_dump_json()) if job else None
        return json.dumps({"replay_job": payload})

    def _submit(self, request: httpx.Request) -> str:
        body = SubmitReplayResultRequest.model_validate_json(request.content)
        self.submitted.append(body)
        job = make_job(id=body.replay_job_id, status=ReplayJobStatus.succeeded)
        return json.dumps({"replay_job": json.loads(job.model_dump_json())})

    def _diagnosis(self, request: httpx.Request) -> str:
        if request.method == "POST":
            run_id = CreateDiagnosisRequest.model_validate_json(request.content).run_id
        else:
            run_id = uuid4()
        status = self.diagnosis_statuses.pop(0)
        diagnosis = Diagnosis(
            id=UUID(int=7),
            run_id=run_id,
            status=status,
            verdict_kind=None,
            first_domino_step=4 if status == DiagnosisStatus.done else None,
            search_low=None,
            search_high=None,
            verify_passes=None,
            verify_samples=None,
            fixed_output=None,
            explanation=None,
            cause_id=None,
            check_count=0,
            replay_count=0,
            cost_usd=0.0,
            error_code=None,
            created_by_id=None,
            created_at=NOW,
            finished_at=None,
        )
        return json.dumps({"diagnosis": json.loads(diagnosis.model_dump_json())})


def fake_client(api: FakeApi, *, key: str | None = "fd_live_test") -> FirstDominoClient:
    """Return a client whose requests go to `api`; `key=None` gives a dark client."""
    settings = SdkSettings(
        api_key=SecretStr(key) if key else None,
        base_url="http://first-domino.test",
        lease_wait_seconds=0,
        diagnosis_poll_seconds=0.001,
        worker_retry_seconds=0,
    )
    http = httpx.AsyncClient(transport=httpx.MockTransport(api.handler))
    return FirstDominoClient(settings, http)
