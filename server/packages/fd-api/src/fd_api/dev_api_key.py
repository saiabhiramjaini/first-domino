"""Creates a project API key for local development without the web app (`make dev-key`).

Signs in a fixed local person (creating their project the first time) and writes a new key
to stdout. The key is shown only here, like `createApiKey`.
"""

import asyncio
import sys

from fd_api.auth.api_keys import create_api_key
from fd_api.auth.users import WebTokenClaims, sign_in
from fd_database.session import Database
from fd_shared.logging import configure_logging

LOCAL_PERSON = WebTokenClaims(sub="local-dev", email="dev@localhost", name="Local developer")
KEY_NAME = "local development"


async def create_dev_api_key() -> str:
    """Returns a new API key for the local developer's project."""
    database = Database()
    try:
        await database.migrate()
        async with database.transaction() as session:
            person = await sign_in(session, LOCAL_PERSON)
            created = await create_api_key(
                session, project_id=person.project_id, name=KEY_NAME, created_by_id=person.user_id
            )
        return created.secret
    finally:
        await database.dispose()


def main() -> None:
    """Writes the key to stdout so it can be copied into `FIRST_DOMINO_API_KEY`."""
    configure_logging()
    sys.stdout.write(f"{asyncio.run(create_dev_api_key())}\n")


if __name__ == "__main__":
    main()
