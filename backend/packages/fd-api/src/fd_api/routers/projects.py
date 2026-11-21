"""Projects routes: the caller's own project and its Slack webhook."""

from fastapi import APIRouter

from fd_api import examples
from fd_api.auth.callers import AnyCaller, PersonCaller
from fd_api.errors import error_responses
from fd_api.models.projects import (
    GetProjectSelfResponse,
    SetProjectSlackWebhookRequest,
    SetProjectSlackWebhookResponse,
)
from fd_shared.enums import ApiErrorCode

router = APIRouter(prefix="/v1", tags=["projects"])


@router.get(
    "/projects.self",
    operation_id="getProjectSelf",
    summary="Get the caller's project",
    responses=error_responses(ApiErrorCode.UNAUTHENTICATED),
)
async def get_project_self(caller: AnyCaller) -> GetProjectSelfResponse:
    """Returns the project the token or API key belongs to."""
    return GetProjectSelfResponse(project=examples.PROJECT)


@router.post(
    "/projects.setSlackWebhook",
    operation_id="setProjectSlackWebhook",
    summary="Set or clear the Slack webhook",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def set_project_slack_webhook(
    body: SetProjectSlackWebhookRequest, caller: PersonCaller
) -> SetProjectSlackWebhookResponse:
    """Sets the Slack incoming webhook that hears about each new cause, or clears it."""
    webhook_set = body.webhook_url is not None
    project = examples.PROJECT.model_copy(update={"slack_webhook_set": webhook_set})
    return SetProjectSlackWebhookResponse(project=project)
