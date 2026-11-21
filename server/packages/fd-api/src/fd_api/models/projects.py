"""Project contract models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from fd_database import tables


class Project(BaseModel):
    """The tenant. Every run, diagnosis and cause belongs to one project."""

    id: UUID
    name: str = Field(max_length=256, description="Display name of the project.")
    slack_webhook_set: bool = Field(
        description="Whether a Slack webhook is set. The URL itself is never returned."
    )
    created_at: datetime = Field(description="Time of creation, in UTC RFC 3339 format.")
    updated_at: datetime = Field(description="Time of the last change, in UTC RFC 3339 format.")

    @classmethod
    def from_row(cls, row: tables.Project) -> "Project":
        """Maps a stored project to the contract."""
        return cls(
            id=row.id,
            name=row.name,
            slack_webhook_set=row.slack_webhook_url is not None,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class GetProjectSelfResponse(BaseModel):
    """The caller's project."""

    project: Project


class SetProjectSlackWebhookRequest(BaseModel):
    """Sets or clears the Slack incoming webhook that hears about new causes."""

    webhook_url: HttpUrl | None = Field(
        description="Slack incoming webhook URL, or null to stop sending messages."
    )


class SetProjectSlackWebhookResponse(BaseModel):
    """The updated project."""

    project: Project
