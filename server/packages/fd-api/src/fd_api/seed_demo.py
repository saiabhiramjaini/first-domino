"""Prepares the demo workspace (`make seed-demo EMAIL=...`).

Gives the person with this email a project named "Call assistant (demo)", inviting them first when
they have never signed in, and writes a new API key for that project to stdout. The demo
worker and recorder use the key, so their runs land in the workspace the person sees on sign-in.
"""

import argparse
import asyncio
import sys

from pydantic import BaseModel, ConfigDict, Field

from fd_api.auth.api_keys import create_api_key
from fd_database.repositories import ProjectsRepository
from fd_database.session import Database
from fd_shared.logging import configure_logging, get_logger

log = get_logger(__name__)

DEMO_PROJECT_NAME = "Call assistant (demo)"
DEMO_KEY_NAME = "demo worker"
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class DemoSeed(BaseModel):
    """Who owns the demo workspace and what it is called."""

    model_config = ConfigDict(frozen=True)

    email: str = Field(pattern=EMAIL_PATTERN)
    project_name: str = DEMO_PROJECT_NAME


async def seed_demo(database: Database, seed: DemoSeed) -> str:
    """Creates or renames the owner's project and returns a new API key for it."""
    async with database.transaction() as session:
        projects = ProjectsRepository(session)
        user = await projects.get_user_by_email(email=seed.email)
        if user is None:
            user = await projects.create_pending_user(email=seed.email, name=seed.email)
        project = await projects.get_owned(owner_id=user.id)
        if project is None:
            project = await projects.create(owner_id=user.id, name=seed.project_name)
        await projects.rename(project=project, name=seed.project_name)
        created = await create_api_key(
            session, project_id=project.id, name=DEMO_KEY_NAME, created_by_id=user.id
        )
    log.info("seed_demo.done", project_id=str(project.id), api_key_id=str(created.api_key.id))
    return created.secret


def main() -> None:
    """Parses `--email`, seeds, and writes the key for `FIRST_DOMINO_API_KEY` to stdout."""
    parser = argparse.ArgumentParser(description="Prepare the demo workspace for one person.")
    parser.add_argument("--email", required=True, help="Google account email of the owner.")
    parser.add_argument("--project-name", default=DEMO_PROJECT_NAME)
    arguments = parser.parse_args()
    configure_logging()
    seed = DemoSeed(email=arguments.email, project_name=arguments.project_name)
    sys.stdout.write(f"{asyncio.run(_seed_with_new_database(seed))}\n")


async def _seed_with_new_database(seed: DemoSeed) -> str:
    database = Database()
    try:
        await database.create_tables()
        return await seed_demo(database, seed)
    finally:
        await database.dispose()


if __name__ == "__main__":
    main()
