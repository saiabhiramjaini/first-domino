"""Wire models generated from api/openapi.json by make sdk-models. Do not edit."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AnyUrl, AwareDatetime, BaseModel, Field, RootModel


class ApiErrorCode(StrEnum):
    bad_request = "bad_request"
    unauthenticated = "unauthenticated"
    permission_denied = "permission_denied"
    not_found = "not_found"
    conflict = "conflict"
    validation_failed = "validation_failed"
    internal_error = "internal_error"


class ApiInternalError(BaseModel):
    code: ApiErrorCode
    title: Annotated[
        str,
        Field(
            description="Short summary of the error. Do not branch on it.",
            title="Title",
        ),
    ]
    detail: Annotated[
        str,
        Field(
            description="What went wrong and what to do. Do not branch on it.",
            title="Detail",
        ),
    ]
    request_id: Annotated[
        str,
        Field(description="Id to quote when reporting the error.", title="Request Id"),
    ]


class ApiKey(BaseModel):
    id: Annotated[UUID, Field(title="Id")]
    name: Annotated[
        str,
        Field(
            description="Name given at creation, such as `staging`.",
            max_length=128,
            title="Name",
        ),
    ]
    prefix: Annotated[
        str,
        Field(
            description="First 12 characters of the key, for telling keys apart.",
            title="Prefix",
        ),
    ]
    created_at: Annotated[
        AwareDatetime,
        Field(description="Time of creation, in UTC RFC 3339 format.", title="Created At"),
    ]
    created_by_id: Annotated[
        UUID,
        Field(description="Id of the person who created the key.", title="Created By Id"),
    ]
    last_used_at: Annotated[
        AwareDatetime | None,
        Field(
            description="Time of the last request with this key, in UTC RFC 3339 format.",
            title="Last Used At",
        ),
    ]
    revoked_at: Annotated[
        AwareDatetime | None,
        Field(
            description="Time of revocation, in UTC RFC 3339 format. Null while the key works.",
            title="Revoked At",
        ),
    ]
    revoked_by_id: Annotated[
        UUID | None,
        Field(description="Id of the person who revoked the key.", title="Revoked By Id"),
    ]


class BenchmarkMethod(StrEnum):
    first_domino = "first_domino"
    read_trace_judge = "read_trace_judge"


class VerifiedRate(RootModel[float]):
    root: Annotated[
        float,
        Field(
            description="Share of runs with a fix proven by replay. Null without proof.",
            ge=0.0,
            le=1.0,
            title="Verified Rate",
        ),
    ]


class BenchmarkScore(BaseModel):
    method: BenchmarkMethod
    runs_scored: Annotated[
        int,
        Field(
            description="Number of labelled runs the method was scored on.",
            ge=0,
            title="Runs Scored",
        ),
    ]
    exact_accuracy: Annotated[
        float,
        Field(
            description="Share of runs where it named the labelled step exactly.",
            ge=0.0,
            le=1.0,
            title="Exact Accuracy",
        ),
    ]
    within_one_accuracy: Annotated[
        float,
        Field(
            description="Share of runs where it was at most one step off.",
            ge=0.0,
            le=1.0,
            title="Within One Accuracy",
        ),
    ]
    verified_rate: Annotated[
        VerifiedRate | None,
        Field(
            description="Share of runs with a fix proven by replay. Null without proof.",
            title="Verified Rate",
        ),
    ]
    mean_cost_usd: Annotated[
        float,
        Field(
            description="Mean model cost per run, in US dollars.",
            ge=0.0,
            title="Mean Cost Usd",
        ),
    ]
    mean_seconds: Annotated[
        float,
        Field(
            description="Mean wall time per run, in seconds.",
            ge=0.0,
            title="Mean Seconds",
        ),
    ]


class CauseCategory(StrEnum):
    wrong_date = "wrong_date"
    wrong_entity = "wrong_entity"
    wrong_filter = "wrong_filter"
    bad_tool_args = "bad_tool_args"
    hallucination = "hallucination"
    tool_issue = "tool_issue"
    other = "other"


class CheckPhase(StrEnum):
    precheck = "precheck"
    bisect = "bisect"
    verify = "verify"
    fallback = "fallback"


class CheckResult(StrEnum):
    pending = "pending"
    can_succeed = "can_succeed"
    doomed = "doomed"


class CountCausesRequest(BaseModel):
    categories: Annotated[
        list[CauseCategory] | None,
        Field(description="Only causes in one of these categories.", title="Categories"),
    ] = None


class CountCausesResponse(BaseModel):
    count: Annotated[int, Field(description="Number of matching objects.", ge=0, title="Count")]


class CountDiagnosesResponse(BaseModel):
    count: Annotated[int, Field(description="Number of matching objects.", ge=0, title="Count")]


class AgentName(RootModel[str]):
    root: Annotated[
        str,
        Field(description="Only runs of this agent.", max_length=128, title="Agent Name"),
    ]


class CountRunsResponse(BaseModel):
    count: Annotated[int, Field(description="Number of matching objects.", ge=0, title="Count")]


class CreateApiKeyRequest(BaseModel):
    name: Annotated[
        str,
        Field(
            description="Name to tell the key apart.",
            max_length=128,
            min_length=1,
            title="Name",
        ),
    ]


class CreateApiKeyResponse(BaseModel):
    api_key: ApiKey
    secret: Annotated[
        str,
        Field(description="The full key. Shown only here; store it now.", title="Secret"),
    ]


class CreateDiagnosisRequest(BaseModel):
    run_id: Annotated[UUID, Field(title="Run Id")]


class DiagnosisStatus(StrEnum):
    queued = "queued"
    bisecting = "bisecting"
    verifying = "verifying"
    explaining = "explaining"
    done = "done"
    failed = "failed"


class Explanation(BaseModel):
    title: Annotated[str, Field(description="Short name of the mistake.", title="Title")]
    summary: Annotated[
        str,
        Field(
            description="What went wrong at the step and why it doomed the run.",
            title="Summary",
        ),
    ]
    suggested_fix: Annotated[
        str,
        Field(
            description="What to change in the agent so it stops happening.",
            title="Suggested Fix",
        ),
    ]
    category: CauseCategory


class FieldError(BaseModel):
    field: Annotated[
        str,
        Field(
            description="Dotted path of the field, such as `task_input.prompt`.",
            title="Field",
        ),
    ]
    message: Annotated[str, Field(description="Why the value was rejected.", title="Message")]


class HealthResponse(BaseModel):
    ok: Annotated[bool, Field(title="Ok")]


class LeaseReplayJobRequest(BaseModel):
    agent_names: Annotated[
        list[str],
        Field(
            description="Agents this worker can run. Only their jobs are leased.",
            min_length=1,
            title="Agent Names",
        ),
    ]
    wait_seconds: Annotated[
        int | None,
        Field(
            description="How long to wait for a job before answering with none.",
            ge=0,
            le=20,
            title="Wait Seconds",
        ),
    ] = 10


class ListApiKeysRequest(BaseModel):
    limit: Annotated[
        int | None,
        Field(
            description="Most items to return in this page.",
            ge=1,
            le=100,
            title="Limit",
        ),
    ] = 50
    cursor: Annotated[
        str | None,
        Field(
            description="The previous page's `next_cursor`, or null for the first page.",
            title="Cursor",
        ),
    ] = None


class ListApiKeysResponse(BaseModel):
    items: Annotated[list[ApiKey], Field(description="The items in this page.", title="Items")]
    next_cursor: Annotated[
        str | None,
        Field(
            description="Cursor for the next page, or null on the last page.",
            title="Next Cursor",
        ),
    ]


class ListCausesRequest(BaseModel):
    categories: Annotated[
        list[CauseCategory] | None,
        Field(description="Only causes in one of these categories.", title="Categories"),
    ] = None
    limit: Annotated[
        int | None,
        Field(
            description="Most items to return in this page.",
            ge=1,
            le=100,
            title="Limit",
        ),
    ] = 50
    cursor: Annotated[
        str | None,
        Field(
            description="The previous page's `next_cursor`, or null for the first page.",
            title="Cursor",
        ),
    ] = None


class ListChecksRequest(BaseModel):
    limit: Annotated[
        int | None,
        Field(
            description="Most items to return in this page.",
            ge=1,
            le=100,
            title="Limit",
        ),
    ] = 50
    cursor: Annotated[
        str | None,
        Field(
            description="The previous page's `next_cursor`, or null for the first page.",
            title="Cursor",
        ),
    ] = None
    diagnosis_id: Annotated[UUID, Field(title="Diagnosis Id")]


class ListStepsRequest(BaseModel):
    limit: Annotated[
        int | None,
        Field(
            description="Most items to return in this page.",
            ge=1,
            le=100,
            title="Limit",
        ),
    ] = 50
    cursor: Annotated[
        str | None,
        Field(
            description="The previous page's `next_cursor`, or null for the first page.",
            title="Cursor",
        ),
    ] = None
    run_id: Annotated[UUID, Field(title="Run Id")]


class MessageRole(StrEnum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class Project(BaseModel):
    id: Annotated[UUID, Field(title="Id")]
    name: Annotated[
        str,
        Field(description="Display name of the project.", max_length=256, title="Name"),
    ]
    slack_webhook_set: Annotated[
        bool,
        Field(
            description="Whether a Slack webhook is set. The URL itself is never returned.",
            title="Slack Webhook Set",
        ),
    ]
    created_at: Annotated[
        AwareDatetime,
        Field(description="Time of creation, in UTC RFC 3339 format.", title="Created At"),
    ]
    updated_at: Annotated[
        AwareDatetime,
        Field(
            description="Time of the last change, in UTC RFC 3339 format.",
            title="Updated At",
        ),
    ]


class ReplayJobStatus(StrEnum):
    queued = "queued"
    leased = "leased"
    succeeded = "succeeded"
    failed = "failed"
    expired = "expired"


class ReplayOutcome(StrEnum):
    passed = "passed"
    failed = "failed"
    errored = "errored"


class RevokeApiKeyRequest(BaseModel):
    api_key_id: Annotated[UUID, Field(title="Api Key Id")]


class RevokeApiKeyResponse(BaseModel):
    api_key: ApiKey


class RunOutcome(StrEnum):
    passed = "passed"
    failed = "failed"
    errored = "errored"


class RunSource(StrEnum):
    recorded = "recorded"
    replay = "replay"


class RunStatus(StrEnum):
    running = "running"
    passed = "passed"
    failed = "failed"
    errored = "errored"


class WebhookUrl(RootModel[AnyUrl]):
    root: Annotated[
        AnyUrl,
        Field(
            description="Slack incoming webhook URL, or null to stop sending messages.",
            title="Webhook Url",
        ),
    ]


class SetProjectSlackWebhookRequest(BaseModel):
    webhook_url: Annotated[
        WebhookUrl | None,
        Field(
            description="Slack incoming webhook URL, or null to stop sending messages.",
            title="Webhook Url",
        ),
    ]


class SetProjectSlackWebhookResponse(BaseModel):
    project: Project


class ErrorCode(RootModel[str]):
    root: Annotated[
        str,
        Field(
            description="The worker's own code for a crash, when `outcome` is `errored`.",
            max_length=128,
            title="Error Code",
        ),
    ]


class SubmitReplayResultRequest(BaseModel):
    replay_job_id: Annotated[UUID, Field(title="Replay Job Id")]
    outcome: ReplayOutcome
    replay_run_id: Annotated[
        UUID | None,
        Field(
            description="The run started for this replay, if one was started.",
            title="Replay Run Id",
        ),
    ] = None
    error_code: Annotated[
        ErrorCode | None,
        Field(
            description="The worker's own code for a crash, when `outcome` is `errored`.",
            title="Error Code",
        ),
    ] = None


class TaskInput(BaseModel):
    prompt: Annotated[str, Field(description="The task given to the agent.", title="Prompt")]
    metadata: Annotated[
        dict[str, str] | None,
        Field(
            description="Customer data the success check needs, such as a `task_id`.",
            title="Metadata",
        ),
    ] = None


class ToolCall(BaseModel):
    id: Annotated[
        str,
        Field(description="Tool call id, minted by the model provider.", title="Id"),
    ]
    name: Annotated[str, Field(description="Name of the tool the model called.", title="Name")]
    arguments: Annotated[
        str,
        Field(
            description="Arguments as JSON text, exactly as the provider returned.",
            title="Arguments",
        ),
    ]


class VerdictKind(StrEnum):
    step_verified = "step_verified"
    step_unverified = "step_unverified"
    multiple_causes = "multiple_causes"
    task_or_tool_issue = "task_or_tool_issue"


class ApiError(BaseModel):
    code: ApiErrorCode
    title: Annotated[
        str,
        Field(
            description="Short summary of the error. Do not branch on it.",
            title="Title",
        ),
    ]
    detail: Annotated[
        str,
        Field(
            description="What went wrong and what to do. Do not branch on it.",
            title="Detail",
        ),
    ]


class ApiValidationError(BaseModel):
    code: ApiErrorCode
    title: Annotated[
        str,
        Field(
            description="Short summary of the error. Do not branch on it.",
            title="Title",
        ),
    ]
    detail: Annotated[
        str,
        Field(
            description="What went wrong and what to do. Do not branch on it.",
            title="Detail",
        ),
    ]
    errors: Annotated[list[FieldError], Field(description="Each invalid field.", title="Errors")]


class Benchmark(BaseModel):
    id: Annotated[UUID, Field(title="Id")]
    created_at: Annotated[
        AwareDatetime,
        Field(
            description="Time the benchmark finished, in UTC RFC 3339 format.",
            title="Created At",
        ),
    ]
    scores: Annotated[
        list[BenchmarkScore], Field(description="One score per method.", title="Scores")
    ]


class Cause(BaseModel):
    id: Annotated[UUID, Field(title="Id")]
    title: Annotated[
        str,
        Field(description="Short name of the mistake.", max_length=256, title="Title"),
    ]
    category: CauseCategory
    step_name: Annotated[
        str,
        Field(
            description="The tool the first domino step called, or its role label.",
            max_length=128,
            title="Step Name",
        ),
    ]
    summary: Annotated[
        str,
        Field(description="What goes wrong and why it dooms the run.", title="Summary"),
    ]
    suggested_fix: Annotated[
        str,
        Field(
            description="What to change in the agent so it stops happening.",
            title="Suggested Fix",
        ),
    ]
    run_count: Annotated[
        int,
        Field(
            description="Number of diagnosed runs with this cause.",
            ge=0,
            title="Run Count",
        ),
    ]
    verified_count: Annotated[
        int,
        Field(
            description="Number of those runs where a fix was proven by replay.",
            ge=0,
            title="Verified Count",
        ),
    ]
    first_seen_at: Annotated[
        AwareDatetime,
        Field(
            description="Time of the first diagnosis with this cause, in UTC RFC 3339 format.",
            title="First Seen At",
        ),
    ]
    last_seen_at: Annotated[
        AwareDatetime,
        Field(
            description="Time of the latest diagnosis with this cause, in UTC RFC 3339 format.",
            title="Last Seen At",
        ),
    ]


class Check(BaseModel):
    id: Annotated[UUID, Field(title="Id")]
    diagnosis_id: Annotated[UUID, Field(title="Diagnosis Id")]
    index: Annotated[
        int,
        Field(description="Order of the check within its diagnosis.", ge=0, title="Index"),
    ]
    phase: CheckPhase
    save_point: Annotated[
        int,
        Field(
            description="Steps 1 to `save_point` are kept as recorded; the rest are replayed.",
            ge=0,
            title="Save Point",
        ),
    ]
    samples: Annotated[int, Field(description="Number of replays run.", ge=0, title="Samples")]
    passes: Annotated[
        int,
        Field(
            description="Number of replays that passed the success check.",
            ge=0,
            title="Passes",
        ),
    ]
    result: CheckResult
    created_at: Annotated[
        AwareDatetime,
        Field(
            description="Time the check started, in UTC RFC 3339 format.",
            title="Created At",
        ),
    ]
    finished_at: Annotated[
        AwareDatetime | None,
        Field(
            description="Time the check finished, in UTC RFC 3339 format. Null while pending.",
            title="Finished At",
        ),
    ]


class CountDiagnosesRequest(BaseModel):
    run_ids: Annotated[
        list[UUID] | None,
        Field(description="Only diagnoses of these runs.", title="Run Ids"),
    ] = None
    cause_ids: Annotated[
        list[UUID] | None,
        Field(description="Only diagnoses in these cause groups.", title="Cause Ids"),
    ] = None
    statuses: Annotated[
        list[DiagnosisStatus] | None,
        Field(description="Only diagnoses with one of these statuses.", title="Statuses"),
    ] = None
    verdict_kinds: Annotated[
        list[VerdictKind] | None,
        Field(
            description="Only diagnoses with one of these verdicts.",
            title="Verdict Kinds",
        ),
    ] = None


class CountRunsRequest(BaseModel):
    statuses: Annotated[
        list[RunStatus] | None,
        Field(description="Only runs with one of these statuses.", title="Statuses"),
    ] = None
    sources: Annotated[
        list[RunSource] | None,
        Field(
            description="Only runs from one of these sources. Recorded runs only unless set.",
            title="Sources",
        ),
    ] = None
    agent_name: Annotated[
        AgentName | None,
        Field(description="Only runs of this agent.", title="Agent Name"),
    ] = None


class FinishRunRequest(BaseModel):
    run_id: Annotated[UUID, Field(title="Run Id")]
    status: RunOutcome
    final_output: Annotated[
        str | None, Field(description="The agent's final answer.", title="Final Output")
    ] = None


class GetCauseResponse(BaseModel):
    cause: Cause


class GetLatestBenchmarkResponse(BaseModel):
    benchmark: Benchmark | None


class GetProjectSelfResponse(BaseModel):
    project: Project


class ListCausesResponse(BaseModel):
    items: Annotated[list[Cause], Field(description="The items in this page.", title="Items")]
    next_cursor: Annotated[
        str | None,
        Field(
            description="Cursor for the next page, or null on the last page.",
            title="Next Cursor",
        ),
    ]


class ListChecksResponse(BaseModel):
    items: Annotated[list[Check], Field(description="The items in this page.", title="Items")]
    next_cursor: Annotated[
        str | None,
        Field(
            description="Cursor for the next page, or null on the last page.",
            title="Next Cursor",
        ),
    ]


class ListDiagnosesRequest(BaseModel):
    run_ids: Annotated[
        list[UUID] | None,
        Field(description="Only diagnoses of these runs.", title="Run Ids"),
    ] = None
    cause_ids: Annotated[
        list[UUID] | None,
        Field(description="Only diagnoses in these cause groups.", title="Cause Ids"),
    ] = None
    statuses: Annotated[
        list[DiagnosisStatus] | None,
        Field(description="Only diagnoses with one of these statuses.", title="Statuses"),
    ] = None
    verdict_kinds: Annotated[
        list[VerdictKind] | None,
        Field(
            description="Only diagnoses with one of these verdicts.",
            title="Verdict Kinds",
        ),
    ] = None
    limit: Annotated[
        int | None,
        Field(
            description="Most items to return in this page.",
            ge=1,
            le=100,
            title="Limit",
        ),
    ] = 50
    cursor: Annotated[
        str | None,
        Field(
            description="The previous page's `next_cursor`, or null for the first page.",
            title="Cursor",
        ),
    ] = None


class ListRunsRequest(BaseModel):
    statuses: Annotated[
        list[RunStatus] | None,
        Field(description="Only runs with one of these statuses.", title="Statuses"),
    ] = None
    sources: Annotated[
        list[RunSource] | None,
        Field(
            description="Only runs from one of these sources. Recorded runs only unless set.",
            title="Sources",
        ),
    ] = None
    agent_name: Annotated[
        AgentName | None,
        Field(description="Only runs of this agent.", title="Agent Name"),
    ] = None
    limit: Annotated[
        int | None,
        Field(
            description="Most items to return in this page.",
            ge=1,
            le=100,
            title="Limit",
        ),
    ] = 50
    cursor: Annotated[
        str | None,
        Field(
            description="The previous page's `next_cursor`, or null for the first page.",
            title="Cursor",
        ),
    ] = None


class Message(BaseModel):
    role: MessageRole
    content: Annotated[
        str | None,
        Field(
            description="Text of the message, or null when it has none.",
            title="Content",
        ),
    ]
    tool_calls: Annotated[
        list[ToolCall] | None,
        Field(
            description="Tool calls in an assistant message. Empty when none.",
            title="Tool Calls",
        ),
    ] = None
    tool_call_id: Annotated[
        str | None,
        Field(
            description="On a `tool` message, the id of the call it answers.",
            title="Tool Call Id",
        ),
    ] = None


class RecordStepRequest(BaseModel):
    run_id: Annotated[UUID, Field(title="Run Id")]
    index: Annotated[
        int,
        Field(description="Position in the run, starting at 1.", ge=1, title="Index"),
    ]
    model: Annotated[
        str,
        Field(
            description="Model id the step called.",
            max_length=128,
            min_length=1,
            title="Model",
        ),
    ]
    output: Annotated[Message, Field(description="The assistant message the model returned.")]
    tool_results: Annotated[
        list[Message] | None,
        Field(
            description="The `tool` messages answering the output's tool calls.",
            title="Tool Results",
        ),
    ] = None
    messages: Annotated[
        list[Message],
        Field(description="Every message in the run after this step.", title="Messages"),
    ]
    tokens_in: Annotated[
        int,
        Field(description="Prompt tokens of the model call.", ge=0, title="Tokens In"),
    ]
    tokens_out: Annotated[
        int,
        Field(description="Completion tokens of the model call.", ge=0, title="Tokens Out"),
    ]
    latency_ms: Annotated[
        int,
        Field(
            description="Duration of the model call, in milliseconds.",
            ge=0,
            title="Latency Ms",
        ),
    ]


class ReplayJob(BaseModel):
    id: Annotated[UUID, Field(title="Id")]
    run_id: Annotated[UUID, Field(description="The recorded run to replay.", title="Run Id")]
    agent_name: Annotated[
        str, Field(description="The agent the worker must run.", title="Agent Name")
    ]
    task_input: TaskInput
    from_step: Annotated[
        int,
        Field(
            description="Keep steps 1 to `from_step` as recorded. 0 means start fresh.",
            ge=0,
            title="From Step",
        ),
    ]
    messages: Annotated[
        list[Message],
        Field(
            description="Messages to resume from, as saved after step `from_step`.",
            title="Messages",
        ),
    ]
    replacement_output: Annotated[
        Message | None,
        Field(
            description="When set, use it as the next model output instead of calling the model."
        ),
    ]
    model_override: Annotated[
        str | None,
        Field(
            description="When set, run the rest of the replay with this model id.",
            title="Model Override",
        ),
    ]
    status: ReplayJobStatus
    lease_expires_at: Annotated[
        AwareDatetime | None,
        Field(
            description="Time the current lease ends, in UTC RFC 3339 format. Null unless leased.",
            title="Lease Expires At",
        ),
    ]
    attempt: Annotated[
        int,
        Field(
            description="Number of times the job has been leased.",
            ge=0,
            title="Attempt",
        ),
    ]


class Run(BaseModel):
    id: Annotated[UUID, Field(title="Id")]
    agent_name: Annotated[
        str,
        Field(
            description="The customer's name for the agent, such as `booker`.",
            title="Agent Name",
        ),
    ]
    source: RunSource
    parent_run_id: Annotated[
        UUID | None,
        Field(
            description="For a replay, the recorded run it replays. Null for a recorded run.",
            title="Parent Run Id",
        ),
    ]
    replay_job_id: Annotated[
        UUID | None,
        Field(
            description="For a replay, the job that asked for it.",
            title="Replay Job Id",
        ),
    ]
    replay_from_step: Annotated[
        int | None,
        Field(
            description="For a replay, the last step kept from the parent run (0 means none).",
            title="Replay From Step",
        ),
    ]
    task_input: TaskInput
    status: RunStatus
    step_count: Annotated[
        int,
        Field(description="Number of steps recorded so far.", ge=0, title="Step Count"),
    ]
    final_output: Annotated[
        str | None,
        Field(
            description="The agent's final answer, if it gave one.",
            title="Final Output",
        ),
    ]
    latest_diagnosis_id: Annotated[
        UUID | None,
        Field(description="The newest diagnosis of this run.", title="Latest Diagnosis Id"),
    ]
    created_by_id: Annotated[
        UUID,
        Field(
            description="Id of the API key that recorded the run.",
            title="Created By Id",
        ),
    ]
    started_at: Annotated[
        AwareDatetime,
        Field(
            description="Time the run started, in UTC RFC 3339 format.",
            title="Started At",
        ),
    ]
    finished_at: Annotated[
        AwareDatetime | None,
        Field(
            description="Time the run finished, in UTC RFC 3339 format. Null while running.",
            title="Finished At",
        ),
    ]


class StartRunRequest(BaseModel):
    agent_name: Annotated[
        str,
        Field(
            description="The customer's name for the agent. Replay jobs are routed by it.",
            max_length=128,
            min_length=1,
            title="Agent Name",
        ),
    ]
    task_input: TaskInput
    replay_job_id: Annotated[
        UUID | None,
        Field(
            description="The leased replay job this run carries out, if any.",
            title="Replay Job Id",
        ),
    ] = None


class StartRunResponse(BaseModel):
    run: Run


class Step(BaseModel):
    id: Annotated[UUID, Field(title="Id")]
    run_id: Annotated[UUID, Field(title="Run Id")]
    index: Annotated[
        int,
        Field(description="Position in the run, starting at 1.", ge=1, title="Index"),
    ]
    model: Annotated[
        str,
        Field(
            description="Model id the step called, as the provider names it.",
            title="Model",
        ),
    ]
    output: Annotated[Message, Field(description="The assistant message the model returned.")]
    tool_results: Annotated[
        list[Message],
        Field(
            description="The `tool` messages answering the output's tool calls.",
            title="Tool Results",
        ),
    ]
    tokens_in: Annotated[
        int,
        Field(description="Prompt tokens of the model call.", ge=0, title="Tokens In"),
    ]
    tokens_out: Annotated[
        int,
        Field(description="Completion tokens of the model call.", ge=0, title="Tokens Out"),
    ]
    latency_ms: Annotated[
        int,
        Field(
            description="Duration of the model call, in milliseconds.",
            ge=0,
            title="Latency Ms",
        ),
    ]
    created_at: Annotated[
        AwareDatetime,
        Field(
            description="Time the step was recorded, in UTC RFC 3339 format.",
            title="Created At",
        ),
    ]


class StepSnapshot(BaseModel):
    step_id: Annotated[UUID, Field(title="Step Id")]
    messages: Annotated[
        list[Message],
        Field(description="Every message in the run after this step.", title="Messages"),
    ]


class SubmitReplayResultResponse(BaseModel):
    replay_job: ReplayJob


class Diagnosis(BaseModel):
    id: Annotated[UUID, Field(title="Id")]
    run_id: Annotated[
        UUID,
        Field(description="The failed recorded run being diagnosed.", title="Run Id"),
    ]
    status: DiagnosisStatus
    verdict_kind: Annotated[
        VerdictKind | None, Field(description="The conclusion. Null until `done`.")
    ]
    first_domino_step: Annotated[
        int | None,
        Field(
            description="Index of the step that doomed the run, once found.",
            title="First Domino Step",
        ),
    ]
    search_low: Annotated[
        int | None,
        Field(
            description="Lowest step still suspected. Null before the search starts.",
            title="Search Low",
        ),
    ]
    search_high: Annotated[
        int | None,
        Field(
            description="Highest step still suspected. Null before the search starts.",
            title="Search High",
        ),
    ]
    verify_passes: Annotated[
        int | None,
        Field(
            description="Replays from the fixed step that passed. Null before verifying.",
            title="Verify Passes",
        ),
    ]
    verify_samples: Annotated[
        int | None,
        Field(
            description="Replays from the fixed step that ran. Null before verifying.",
            title="Verify Samples",
        ),
    ]
    fixed_output: Annotated[
        Message | None,
        Field(description="The rewritten first domino step used to verify the cause."),
    ]
    explanation: Annotated[
        Explanation | None, Field(description="What went wrong, once explained.")
    ]
    cause_id: Annotated[
        UUID | None,
        Field(description="The cause group this diagnosis joined.", title="Cause Id"),
    ]
    check_count: Annotated[
        int,
        Field(description="Number of checks run so far.", ge=0, title="Check Count"),
    ]
    replay_count: Annotated[
        int,
        Field(description="Number of replays run so far.", ge=0, title="Replay Count"),
    ]
    cost_usd: Annotated[
        float,
        Field(
            description="Model cost of the diagnosis so far, in US dollars.",
            ge=0.0,
            title="Cost Usd",
        ),
    ]
    error_code: Annotated[
        str | None,
        Field(
            description="Stable code of the error that stopped the diagnosis, when `failed`.",
            title="Error Code",
        ),
    ]
    created_by_id: Annotated[
        UUID | None,
        Field(
            description="Id of the person or API key that asked for it. Null for auto-diagnosis.",
            title="Created By Id",
        ),
    ]
    created_at: Annotated[
        AwareDatetime,
        Field(description="Time of creation, in UTC RFC 3339 format.", title="Created At"),
    ]
    finished_at: Annotated[
        AwareDatetime | None,
        Field(
            description="Time it reached `done` or `failed`, in UTC RFC 3339 format.",
            title="Finished At",
        ),
    ]


class FinishRunResponse(BaseModel):
    run: Run


class GetDiagnosisResponse(BaseModel):
    diagnosis: Diagnosis


class GetRunResponse(BaseModel):
    run: Run


class GetStepSnapshotResponse(BaseModel):
    snapshot: StepSnapshot


class LeaseReplayJobResponse(BaseModel):
    replay_job: ReplayJob | None


class ListDiagnosesResponse(BaseModel):
    items: Annotated[list[Diagnosis], Field(description="The items in this page.", title="Items")]
    next_cursor: Annotated[
        str | None,
        Field(
            description="Cursor for the next page, or null on the last page.",
            title="Next Cursor",
        ),
    ]


class ListRunsResponse(BaseModel):
    items: Annotated[list[Run], Field(description="The items in this page.", title="Items")]
    next_cursor: Annotated[
        str | None,
        Field(
            description="Cursor for the next page, or null on the last page.",
            title="Next Cursor",
        ),
    ]


class ListStepsResponse(BaseModel):
    items: Annotated[list[Step], Field(description="The items in this page.", title="Items")]
    next_cursor: Annotated[
        str | None,
        Field(
            description="Cursor for the next page, or null on the last page.",
            title="Next Cursor",
        ),
    ]


class RecordStepResponse(BaseModel):
    step: Step


class CreateDiagnosisResponse(BaseModel):
    diagnosis: Diagnosis
