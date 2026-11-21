"""Users and projects repository."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.tables import Project, User
from fd_database.tables.base import utc_now

PENDING_SUB_PREFIX = "pending:"


def pending_sub(email: str) -> str:
    """The placeholder `google_sub` of a person invited by email who has not signed in yet."""
    return PENDING_SUB_PREFIX + email.strip().lower()


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

    async def create_pending_user(self, *, email: str, name: str) -> User:
        """Invites a person by email. Their first sign-in with that email claims the row."""
        return await self.upsert_user(google_sub=pending_sub(email), email=email, name=name)

    async def claim_pending_user(self, *, email: str, google_sub: str, name: str) -> User | None:
        """Gives an invited person's row their real `google_sub`. None when nobody was invited."""
        statement = (
            update(User)
            .where(User.google_sub == pending_sub(email))
            .values(google_sub=google_sub, name=name, updated_at=utc_now())
            .returning(User)
        )
        return (await self._session.scalars(statement)).one_or_none()

    async def get_user_by_email(self, *, email: str) -> User | None:
        """The earliest person with this email."""
        statement = (
            select(User)
            .where(func.lower(User.email) == email.strip().lower())
            .order_by(User.created_at)
            .limit(1)
        )
        return await self._session.scalar(statement)

    async def rename(self, *, project: Project, name: str) -> Project:
        """Renames a project."""
        project.name = name
        await self._session.flush()
        return project

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
