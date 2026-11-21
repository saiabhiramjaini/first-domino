"""The database scores of stored benchmark rows equal the report's scores.

Accuracy is over every labelled run, and a run with no step named is a miss. Averaging
`predicted_step = true_step` over the rows in SQL without that rule drops those runs, because
the comparison is null for them: that is how 32 hits read as 91% (of 35) instead of 82% (of 39).
"""

from collections.abc import AsyncIterator, Iterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from fd_database.repositories.benchmark import BenchmarkRepository
from fd_database.settings import DatabaseSettings
from fd_database.tables import Base
from fd_database.testing import temporary_test_database
from fd_demo_agent.bugs import BugKind
from fd_scripts.benchmark import stored_rows
from fd_scripts.scoring import CaseResult, score
from fd_shared.enums import BenchmarkMethod, VerdictKind

ENGINE = BenchmarkMethod.FIRST_DOMINO


@pytest.fixture(scope="module")
def database_settings() -> Iterator[DatabaseSettings]:
    with temporary_test_database(DatabaseSettings()) as settings:
        if settings is None:
            pytest.skip("Postgres is not reachable at FD_DATABASE_URL")
        yield settings


@pytest.fixture
async def session(database_settings: DatabaseSettings) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(database_settings.url.get_secret_value(), poolclass=NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.commit()
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            yield session
    await engine.dispose()


def result(case_id: str, predicted: int | None, kind: VerdictKind | None) -> CaseResult:
    return CaseResult(
        method=ENGINE,
        case_id=case_id,
        bug_kind=BugKind.AM_AS_PM,
        true_step=5,
        predicted_step=predicted,
        verified=kind is VerdictKind.STEP_VERIFIED,
        verdict_kind=kind,
        error_code=None,
        cost_usd=0.25,
        seconds=4.0,
    )


RESULTS = [
    result("exact-a", 5, VerdictKind.STEP_VERIFIED),
    result("exact-b", 5, VerdictKind.STEP_VERIFIED),
    result("one-off", 6, VerdictKind.STEP_VERIFIED),
    result("no-step", None, VerdictKind.TASK_OR_TOOL_ISSUE),
]


def test_a_run_with_no_step_named_is_a_miss() -> None:
    scores = score(ENGINE, RESULTS)

    assert scores.runs_scored == 4
    assert scores.exact_accuracy == pytest.approx(0.5)
    assert scores.within_one_accuracy == pytest.approx(0.75)


async def test_database_scores_equal_the_report(session: AsyncSession) -> None:
    repository = BenchmarkRepository(session)
    benchmark = await repository.create(results=stored_rows(RESULTS))

    [stored] = await repository.scores(benchmark_id=benchmark.id)
    report = score(ENGINE, RESULTS)

    assert stored.runs_scored == report.runs_scored
    assert stored.exact_accuracy == pytest.approx(report.exact_accuracy)
    assert stored.within_one_accuracy == pytest.approx(report.within_one_accuracy)
    assert stored.verified_rate == pytest.approx(report.verified_rate)
