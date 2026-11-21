"""Async HTTP client for the First Domino API, typed with the generated wire models."""

from functools import cache
from uuid import UUID

import httpx
from pydantic import BaseModel, ValidationError

from first_domino._generated.models import (
    ApiError,
    CreateDiagnosisRequest,
    CreateDiagnosisResponse,
    Diagnosis,
    FinishRunRequest,
    FinishRunResponse,
    GetDiagnosisResponse,
    GetRunResponse,
    LeaseReplayJobRequest,
    LeaseReplayJobResponse,
    RecordStepRequest,
    RecordStepResponse,
    ReplayJob,
    Run,
    StartRunRequest,
    StartRunResponse,
    Step,
    SubmitReplayResultRequest,
    SubmitReplayResultResponse,
)
from first_domino.errors import ApiRequestError, ConfigurationError
from first_domino.settings import SdkSettings

_API_PREFIX = "/v1"


def _error_from(response: httpx.Response) -> ApiRequestError:
    try:
        body = ApiError.model_validate_json(response.content)
    except ValidationError:
        message = f"First Domino API answered {response.status_code}"
        return ApiRequestError(message, status_code=response.status_code, code=None)
    message = f"{body.code}: {body.title}"
    return ApiRequestError(message, status_code=response.status_code, code=body.code)


class FirstDominoClient:
    """Calls the First Domino API with a project API key.

    Use one client per process; it holds a connection pool.

    Example:
        >>> client = FirstDominoClient(SdkSettings(api_key="fd_live_..."))
        >>> run = await client.get_run(run_id)
    """

    def __init__(
        self, settings: SdkSettings | None = None, http: httpx.AsyncClient | None = None
    ) -> None:
        self._settings = settings or SdkSettings()
        self._http = http or httpx.AsyncClient(timeout=self._settings.timeout_seconds)

    @property
    def settings(self) -> SdkSettings:
        """The settings this client was built with."""
        return self._settings

    @property
    def enabled(self) -> bool:
        """True when an API key is set, so calls can succeed."""
        return self._settings.api_key is not None

    async def aclose(self) -> None:
        """Close the connection pool."""
        await self._http.aclose()

    async def start_run(self, request: StartRunRequest) -> Run:
        """Start a recorded run, or a replay run when `replay_job_id` is set."""
        return (await self._post("runs.start", request, StartRunResponse)).run

    async def record_step(self, request: RecordStepRequest) -> Step:
        """Record one step and its message snapshot. Idempotent on (run, index)."""
        return (await self._post("steps.record", request, RecordStepResponse)).step

    async def finish_run(self, request: FinishRunRequest) -> Run:
        """Finish a run as passed, failed or errored."""
        return (await self._post("runs.finish", request, FinishRunResponse)).run

    async def get_run(self, run_id: UUID) -> Run:
        """Return one run."""
        return (await self._get("runs.get", {"run_id": str(run_id)}, GetRunResponse)).run

    async def create_diagnosis(self, request: CreateDiagnosisRequest) -> Diagnosis:
        """Start a diagnosis of a failed recorded run."""
        return (await self._post("diagnoses.create", request, CreateDiagnosisResponse)).diagnosis

    async def get_diagnosis(self, diagnosis_id: UUID) -> Diagnosis:
        """Return one diagnosis."""
        params = {"diagnosis_id": str(diagnosis_id)}
        return (await self._get("diagnoses.get", params, GetDiagnosisResponse)).diagnosis

    async def lease_replay_job(self, request: LeaseReplayJobRequest) -> ReplayJob | None:
        """Wait up to `wait_seconds` for a replay job; None when none arrived."""
        response = await self._post(
            "replay-jobs.lease", request, LeaseReplayJobResponse, server_wait=request.wait_seconds
        )
        return response.replay_job

    async def submit_replay_result(self, request: SubmitReplayResultRequest) -> ReplayJob:
        """Report a replay's outcome. Idempotent by job id."""
        return (
            await self._post("replay-jobs.submit", request, SubmitReplayResultResponse)
        ).replay_job

    def _headers(self) -> dict[str, str]:
        key = self._settings.api_key
        if key is None:
            msg = "FIRST_DOMINO_API_KEY is not set"
            raise ConfigurationError(msg)
        return {"Authorization": f"Bearer {key.get_secret_value()}"}

    def _url(self, action: str) -> str:
        return f"{self._settings.base_url.rstrip('/')}{_API_PREFIX}/{action}"

    async def _post[ResponseT: BaseModel](
        self,
        action: str,
        body: BaseModel,
        response_type: type[ResponseT],
        *,
        server_wait: float | None = None,
    ) -> ResponseT:
        request = self._http.build_request(
            "POST",
            self._url(action),
            content=body.model_dump_json(exclude_unset=True),
            headers={**self._headers(), "Content-Type": "application/json"},
            timeout=(server_wait or 0) + self._settings.timeout_seconds,
        )
        return await self._send(request, response_type)

    async def _get[ResponseT: BaseModel](
        self, action: str, params: dict[str, str], response_type: type[ResponseT]
    ) -> ResponseT:
        request = self._http.build_request(
            "GET", self._url(action), params=params, headers=self._headers()
        )
        return await self._send(request, response_type)

    async def _send[ResponseT: BaseModel](
        self, request: httpx.Request, response_type: type[ResponseT]
    ) -> ResponseT:
        try:
            response = await self._http.send(request)
        except httpx.TransportError as exc:
            msg = f"could not reach the First Domino API: {type(exc).__name__}"
            raise ApiRequestError(msg, status_code=None, code=None) from exc
        if response.is_error:
            raise _error_from(response)
        return response_type.model_validate_json(response.content)


@cache
def default_client() -> FirstDominoClient:
    """Return the process's shared client, built from the environment on first use."""
    return FirstDominoClient()
