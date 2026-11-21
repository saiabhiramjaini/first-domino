"""Projects routes: the caller's own project and its Slack webhook."""

from uuid import UUID

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from fd_api.auth.callers import AnyCaller, PersonCaller
from fd_api.database import DbSession
from fd_api.errors import error_responses
from fd_api.models.projects import (
    GetProjectSelfResponse,
    Project,
    SetProjectSlackWebhookRequest,
    SetProjectSlackWebhookResponse,
)
from fd_database import tables
from fd_database.repositories import ProjectsRepository
from fd_shared.enums import ApiErrorCode
from fd_shared.errors import UnauthenticatedError

router = APIRouter(prefix="/v1", tags=["projects"])


async def _own_project(session: AsyncSession, project_id: UUID) -> tables.Project:
    project = await ProjectsRepository(session).get(project_id=project_id)
    if project is None:
        raise UnauthenticatedError
    return project


@router.get(
    "/projects.self",
    operation_id="getProjectSelf",
    summary="Get the caller's project",
    responses=error_responses(ApiErrorCode.UNAUTHENTICATED),
)
async def get_project_self(caller: AnyCaller, session: DbSession) -> GetProjectSelfResponse:
    """Returns the project the token or API key belongs to."""
    project = await _own_project(session, caller.project_id)
    return GetProjectSelfResponse(project=Project.from_row(project))


@router.post(
    "/projects.setSlackWebhook",
    operation_id="setProjectSlackWebhook",
    summary="Set or clear the Slack webhook",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def set_project_slack_webhook(
    body: SetProjectSlackWebhookRequest, caller: PersonCaller, session: DbSession
) -> SetProjectSlackWebhookResponse:
    """Sets the Slack incoming webhook that hears about each new cause, or clears it."""
    project = await _own_project(session, caller.project_id)
    webhook_url = None if body.webhook_url is None else str(body.webhook_url)
    project = await ProjectsRepository(session).set_slack_webhook(
        project=project, webhook_url=webhook_url
    )
    return SetProjectSlackWebhookResponse(project=Project.from_row(project))
