"""Fixtures for SDK tests."""

import pytest

from first_domino.client import FirstDominoClient
from first_domino.testing import FakeApi, fake_client


@pytest.fixture
def api() -> FakeApi:
    return FakeApi()


@pytest.fixture
def client(api: FakeApi) -> FirstDominoClient:
    return fake_client(api)


@pytest.fixture
def dark_client(api: FakeApi) -> FirstDominoClient:
    return fake_client(api, key=None)
