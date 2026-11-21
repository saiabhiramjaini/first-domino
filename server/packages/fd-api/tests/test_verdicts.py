"""A re-diagnosed run counts only in the cause group of its latest diagnosis."""

from uuid import UUID, uuid4

from fd_api.auth.api_keys import create_api_key
from fd_api.auth.users import WebTokenClaims, sign_in
from fd_api.services.verdicts import store_verdict
from fd_database.repositories import CausesRepository, DiagnosesRepository, RunsRepository
from fd_database.session import Database
from fd_database.tables.base import utc_now
from fd_engine.group import CauseCandidate, CauseMatch
from fd_shared.enums import CauseCategory, VerdictKind
from fd_shared.models import DiagnosisResult, Explanation, TaskInput


class NeverMatch:
    async def match(self, explanation: Explanation, candidates: list[CauseCandidate]) -> CauseMatch:
        return CauseMatch(cause_id=None, cost_usd=0.0)


def _verified(title: str) -> DiagnosisResult:
    return DiagnosisResult(
        verdict_kind=VerdictKind.STEP_VERIFIED,
        first_domino_step=5,
        verify_passes=5,
        verify_samples=5,
        fixed_output=None,
        explanation=Explanation(
            title=title, summary="s", suggested_fix="f", category=CauseCategory.WRONG_DATE
        ),
        check_count=5,
        replay_count=17,
        cost_usd=0.01,
    )


async def _failed_run(database: Database) -> tuple[UUID, UUID]:
    claims = WebTokenClaims(sub=f"google-{uuid4()}", email="v@example.test", name="V")
    async with database.transaction() as session:
        person = await sign_in(session, claims)
        key = await create_api_key(
            session, project_id=person.project_id, name="k", created_by_id=person.user_id
        )
        run = await RunsRepository(session).create(
            project_id=person.project_id,
            agent_name="call-assistant",
            task_input=TaskInput(prompt="Book tomorrow at 10"),
            tool_names=[],
            created_by_id=key.api_key.id,
            started_at=utc_now(),
        )
    return person.project_id, run.id


async def _diagnose(database: Database, project_id: UUID, run_id: UUID, title: str) -> UUID:
    async with database.transaction() as session:
        diagnosis = await DiagnosesRepository(session).create(
            project_id=project_id, run_id=run_id, created_by_id=None
        )
    stored = await store_verdict(
        database,
        NeverMatch(),
        project_id=project_id,
        diagnosis_id=diagnosis.id,
        result=_verified(title),
    )
    assert stored.cause is not None
    return stored.cause.id


async def test_rediagnosed_run_moves_to_its_new_cause(database: Database) -> None:
    await database.create_tables()
    project_id, run_id = await _failed_run(database)

    first = await _diagnose(database, project_id, run_id, "Converted AM to PM")
    second = await _diagnose(database, project_id, run_id, "Resolved tomorrow one day late")

    async with database.transaction() as session:
        causes = CausesRepository(session)
        old = await causes.get(project_id=project_id, cause_id=first)
        new = await causes.get(project_id=project_id, cause_id=second)
    assert old is None
    assert new is not None
    assert (new.run_count, new.verified_count) == (1, 1)
