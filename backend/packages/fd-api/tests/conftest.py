"""Shared fixtures for the API tests."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from fd_api.main import create_app
from fd_api.settings import ApiSettings


@pytest.fixture
def settings() -> ApiSettings:
    return ApiSettings()


@pytest.fixture
async def client(settings: ApiSettings) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=create_app(settings))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
