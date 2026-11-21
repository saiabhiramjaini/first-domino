"""Users and projects repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.tables import Project, User
from fd_database.tables.base import utc_now


class ProjectsRepository:
    """People and the projects they own."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_user(self, *, google_sub: str, email: str, name: str) -> User:
        """Creates the person on first sign-in, or refreshes their email and name."""
        now = utc_now()
        statement = (
            insert(User)
            .values(google_sub=google_sub, email=email, name=name, created_at=now, updated_at=now)
            .on_conflict_do_update(
                index_elements=[User.google_sub],
                set_={"email": email, "name": name, "updated_at": now},
            )
            .returning(User)
        )
        return (await self._session.scalars(statement)).one()

    async def get_owned(self, *, owner_id: UUID) -> Project | None:
        """The project a person owns, if they have one yet."""
        return await self._session.scalar(select(Project).where(Project.owner_id == owner_id))

    async def create(self, *, owner_id: UUID, name: str) -> Project:
        """Creates a person's project. Racing first sign-ins return the same project."""
        now = utc_now()
        statement = (
            insert(Project)
            .values(owner_id=owner_id, name=name, created_at=now, updated_at=now)
            .on_conflict_do_update(index_elements=[Project.owner_id], set_={"updated_at": now})
            .returning(Project)
        )
        return (await self._session.scalars(statement)).one()

    async def get(self, *, project_id: UUID) -> Project | None:
        """One project by id."""
        return await self._session.get(Project, project_id)

    async def set_slack_webhook(self, *, project: Project, webhook_url: str | None) -> Project:
        """Sets or clears the Slack webhook."""
        project.slack_webhook_url = webhook_url
        await self._session.flush()
        return project
