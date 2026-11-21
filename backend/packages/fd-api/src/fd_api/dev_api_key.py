"""Creates a project API key for local development without the web app (`make dev-key`).

Signs in a fixed local person (creating their project the first time) and writes a new key
to stdout. The key is shown only here, like `createApiKey`.
"""

import asyncio
import sys

from fd_api.auth.api_keys import mint_api_key
from fd_api.auth.users import WebTokenClaims, sign_in
from fd_database.repositories import ApiKeysRepository
from fd_database.session import Database
from fd_shared.logging import configure_logging, get_logger

log = get_logger(__name__)

LOCAL_PERSON = WebTokenClaims(sub="local-dev", email="dev@localhost", name="Local developer")
KEY_NAME = "local development"


async def create_dev_api_key() -> str:
    """Returns a new API key for the local developer's project."""
    database = Database()
    try:
        await database.create_tables()
        async with database.transaction() as session:
            person = await sign_in(session, LOCAL_PERSON)
            new_key = mint_api_key()
            api_key = await ApiKeysRepository(session).create(
                project_id=person.project_id,
                name=KEY_NAME,
                prefix=new_key.prefix,
                key_hash=new_key.key_hash,
                created_by_id=person.user_id,
            )
        log.info(
            "dev_api_key.created", project_id=str(person.project_id), api_key_id=str(api_key.id)
        )
        return new_key.secret
    finally:
        await database.dispose()


def main() -> None:
    """Writes the key to stdout so it can be copied into `FIRST_DOMINO_API_KEY`."""
    configure_logging()
    secret = asyncio.run(create_dev_api_key())
    sys.stdout.write(f"{secret}\n")


if __name__ == "__main__":
    main()
