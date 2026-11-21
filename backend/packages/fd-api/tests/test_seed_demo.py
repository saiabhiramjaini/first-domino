"""An invited person's first sign-in lands in the demo workspace prepared for them."""

from httpx import AsyncClient

from fd_api.seed_demo import DemoSeed, seed_demo
from fd_database.session import Database

from .conftest import bearer, web_token


async def test_invited_person_signs_into_the_demo_project(
    client: AsyncClient, database: Database
) -> None:
    secret = await seed_demo(database, DemoSeed(email="Judge.One@Example.test"))
    person = bearer(web_token("google-judge-one", email="judge.one@example.test"))

    by_person = await client.get("/v1/projects.self", headers=person)
    by_key = await client.get("/v1/projects.self", headers=bearer(secret))

    assert by_person.json()["project"]["name"] == "Equal AI (demo)"
    assert by_person.json()["project"]["id"] == by_key.json()["project"]["id"]


async def test_seeding_again_keeps_one_project(client: AsyncClient, database: Database) -> None:
    await seed_demo(database, DemoSeed(email="judge.two@example.test"))
    await seed_demo(database, DemoSeed(email="judge.two@example.test"))
    person = bearer(web_token("google-judge-two", email="judge.two@example.test"))

    projects = await client.get("/v1/projects.self", headers=person)

    assert projects.json()["project"]["name"] == "Equal AI (demo)"
