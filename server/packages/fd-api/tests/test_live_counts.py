"""A running diagnosis counts its checks and replays as they happen, not only at the end."""

from fd_api.adapters.check_sink import DatabaseCheckSink
from fd_database.repositories import DiagnosesRepository
from fd_database.session import Database
from fd_shared.enums import CheckPhase, CheckResult
from fd_shared.models import CheckView

from .test_verdicts import _failed_run


async def test_checks_and_replays_count_up_while_running(database: Database) -> None:
    await database.create_tables()
    project_id, run_id = await _failed_run(database)
    async with database.transaction() as session:
        diagnosis = await DiagnosesRepository(session).create(
            project_id=project_id, run_id=run_id, created_by_id=None
        )
    sink = DatabaseCheckSink(database, project_id)

    for index, save_point in enumerate((0, 4)):
        check = CheckView(
            diagnosis_id=diagnosis.id,
            index=index,
            phase=CheckPhase.PRECHECK if index == 0 else CheckPhase.BISECT,
            save_point=save_point,
            samples=3,
            passes=0,
            result=CheckResult.PENDING,
        )
        await sink.check_started(check)
        async with database.transaction() as session:
            await DiagnosesRepository(session).count_progress(
                project_id=project_id,
                diagnosis_id=diagnosis.id,
                checks_at_least=0,
                replays_added=check.samples,
            )

    async with database.transaction() as session:
        live = await DiagnosesRepository(session).get(
            project_id=project_id, diagnosis_id=diagnosis.id
        )
    assert live is not None
    assert (live.check_count, live.replay_count) == (2, 6)
