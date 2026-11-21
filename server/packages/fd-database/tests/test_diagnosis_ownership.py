"""Recovery fails only diagnoses nobody runs any more, and a finished diagnosis has no error."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.repositories import DiagnosesRepository
from fd_database.tables import Project
from fd_database.tables.base import utc_now
from fd_shared.enums import DiagnosisErrorCode, DiagnosisStatus, VerdictKind

from .test_repositories import _run

ABANDONED_AFTER = timedelta(seconds=60)


async def test_recovery_spares_live_and_new_diagnoses(
    session: AsyncSession, project: Project
) -> None:
    diagnoses = DiagnosesRepository(session)
    live, abandoned, unclaimed = [
        await diagnoses.create(
            project_id=project.id, run_id=(await _run(session, project)).id, created_by_id=None
        )
        for _ in range(3)
    ]
    now = utc_now()
    for diagnosis, last_heartbeat in ((live, now), (abandoned, now - 2 * ABANDONED_AFTER)):
        await diagnoses.claim(
            project_id=project.id, diagnosis_id=diagnosis.id, runner_id=uuid4(), now=last_heartbeat
        )

    failed = await diagnoses.fail_abandoned(
        stale_before=now - ABANDONED_AFTER,
        error_code=DiagnosisErrorCode.INTERRUPTED,
        finished_at=now,
    )

    statuses = [
        (await diagnoses.get(project_id=project.id, diagnosis_id=d.id)).status  # type: ignore[union-attr]
        for d in (live, abandoned, unclaimed)
    ]
    assert failed == 1
    assert statuses == [DiagnosisStatus.QUEUED, DiagnosisStatus.FAILED, DiagnosisStatus.QUEUED]


async def test_heartbeat_keeps_a_claimed_diagnosis_alive(
    session: AsyncSession, project: Project
) -> None:
    diagnoses = DiagnosesRepository(session)
    run = await _run(session, project)
    diagnosis = await diagnoses.create(project_id=project.id, run_id=run.id, created_by_id=None)
    runner_id, start = uuid4(), utc_now() - 2 * ABANDONED_AFTER
    await diagnoses.claim(
        project_id=project.id, diagnosis_id=diagnosis.id, runner_id=runner_id, now=start
    )

    await diagnoses.heartbeat(runner_id=runner_id, now=utc_now())
    failed = await diagnoses.fail_abandoned(
        stale_before=utc_now() - ABANDONED_AFTER,
        error_code=DiagnosisErrorCode.INTERRUPTED,
        finished_at=utc_now(),
    )

    assert failed == 0


async def test_finishing_clears_an_earlier_error_code(
    session: AsyncSession, project: Project
) -> None:
    diagnoses = DiagnosesRepository(session)
    run = await _run(session, project)
    diagnosis = await diagnoses.create(project_id=project.id, run_id=run.id, created_by_id=None)
    await diagnoses.fail(
        diagnosis=diagnosis, error_code=DiagnosisErrorCode.INTERRUPTED, finished_at=utc_now()
    )

    finished = await diagnoses.finish(
        diagnosis=diagnosis,
        verdict_kind=VerdictKind.STEP_VERIFIED,
        first_domino_step=2,
        verify_passes=2,
        verify_samples=2,
        fixed_output=None,
        explanation=None,
        cause_id=None,
        check_count=4,
        replay_count=8,
        cost_usd=Decimal("0.01"),
        finished_at=utc_now(),
    )

    assert (finished.status, finished.error_code) == (DiagnosisStatus.DONE, None)
