"""Migrates the database at `FD_DATABASE_URL`, or writes a new revision for the table changes."""

import argparse
import asyncio

from fd_database.schema import upgrade, write_revision
from fd_database.session import Database
from fd_shared.logging import configure_logging


async def _run(arguments: argparse.Namespace) -> None:
    database = Database()
    try:
        if arguments.command == "revision":
            await write_revision(database.engine, arguments.message)
        else:
            await upgrade(database.engine)
    finally:
        await database.dispose()


def main() -> None:
    """Runs `upgrade` or `revision --message`."""
    parser = argparse.ArgumentParser(description="Migrate the database at FD_DATABASE_URL.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("upgrade", help="Upgrade to the latest revision.")
    revision = commands.add_parser("revision", help="Autogenerate a revision from the tables.")
    revision.add_argument("--message", required=True, help="What the revision changes.")
    configure_logging()
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
