"""Shared fixtures for the API tests.

`client` runs the real app against a throwaway `<database>_test_<random>` on the
`FD_DATABASE_URL` server (start one with `make db-up`), never the database itself, and skips
when the server is unreachable.
`bare_client` needs no database and serves only what runs before auth.
"""

import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from uuid import uuid4

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError

from fd_api.auth.users import WEB_TOKEN_ALGORITHM, WEB_TOKEN_AUDIENCE, WEB_TOKEN_ISSUER
from fd_api.main import create_app
from fd_api.settings import ApiSettings
from fd_database.session import Database
from fd_database.settings import DatabaseSettings
from fd_database.testing import temporary_test_database

from .fake_engine import FakeEngine

TEST_WEB_SECRET = "test-web-secret-that-is-long-enough-for-hs256"

Headers = dict[str, str]


@pytest.fixture
def settings() -> ApiSettings:
    return ApiSettings(
        web_jwt_secret=SecretStr(TEST_WEB_SECRET),
        lease_poll_interval_seconds=0.05,
        replay_poll_interval_seconds=0.05,
    )


@pytest.fixture
async def bare_client(settings: ApiSettings) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=create_app(settings))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
def database_settings() -> Iterator[DatabaseSettings]:
    with temporary_test_database(DatabaseSettings()) as settings:
        if settings is None:
            pytest.skip("Postgres is not reachable at FD_DATABASE_URL")
        yield settings


@pytest.fixture
def database(database_settings: DatabaseSettings) -> Database:
    return Database(database_settings)


@pytest.fixture
async def client(settings: ApiSettings, database: Database) -> AsyncIterator[AsyncClient]:
    app = create_app(settings, database, FakeEngine())
    try:
        lifespan = app.router.lifespan_context(app)
        await lifespan.__aenter__()
    except (OSError, OperationalError):
        pytest.skip("Postgres is not reachable at FD_DATABASE_URL")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await lifespan.__aexit__(None, None, None)


def web_token(sub: str, *, secret: str = TEST_WEB_SECRET, lifetime: int = 3600, **claims) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": f"{sub}@example.test",
        "name": "Test Person",
        "iss": WEB_TOKEN_ISSUER,
        "aud": WEB_TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + lifetime,
        **claims,
    }
    return jwt.encode(payload, secret, algorithm=WEB_TOKEN_ALGORITHM)


def bearer(token: str) -> Headers:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def person() -> Headers:
    return bearer(web_token(f"google-{uuid4()}"))


@pytest.fixture
def make_api_key(client: AsyncClient) -> Callable[[Headers], Awaitable[Headers]]:
    async def make(person_headers: Headers) -> Headers:
        response = await client.post(
            "/v1/api-keys.create", json={"name": "test"}, headers=person_headers
        )
        assert response.status_code == 200, response.text
        return bearer(response.json()["secret"])

    return make


@pytest.fixture
async def api_key(
    make_api_key: Callable[[Headers], Awaitable[Headers]], person: Headers
) -> Headers:
    return await make_api_key(person)
