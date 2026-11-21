"""Recovery fails only diagnoses nobody runs any more, and a finished diagnosis has no error."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.repositories import DiagnosesRepository
from fd_database.tables import Project
from fd_database.tables.base import utc_now
from fd_shared.enums import (
    CheckPhase,
    CheckResult,
    DiagnosisErrorCode,
    DiagnosisStatus,
    VerdictKind,
)

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


async def test_take_over_restarts_recent_abandoned_diagnoses_only(
    session: AsyncSession, project: Project
) -> None:
    diagnoses = DiagnosesRepository(session)
    live, abandoned, too_old = [
        await diagnoses.create(
            project_id=project.id, run_id=(await _run(session, project)).id, created_by_id=None
        )
        for _ in range(3)
    ]
    now = utc_now()
    too_old.created_at = now - timedelta(hours=2)
    for diagnosis, last_heartbeat in (
        (live, now),
        (abandoned, now - 2 * ABANDONED_AFTER),
        (too_old, now - 2 * ABANDONED_AFTER),
    ):
        await diagnoses.claim(
            project_id=project.id, diagnosis_id=diagnosis.id, runner_id=uuid4(), now=last_heartbeat
        )
    check = await diagnoses.save_check(
        project_id=project.id,
        diagnosis_id=abandoned.id,
        index=0,
        phase=CheckPhase.BISECT,
        save_point=1,
        samples=3,
        passes=0,
        drifted=0,
        drift_tool_name=None,
        result=CheckResult.DOOMED,
        finished_at=now,
    )
    replay_run = await _run(session, project)
    replay_run.check_id = check.id
    await session.flush()
    new_owner = uuid4()

    taken = await diagnoses.take_over_abandoned(
        stale_before=now - ABANDONED_AFTER,
        created_after=now - timedelta(hours=1),
        runner_id=new_owner,
        now=now,
    )

    assert [d.id for d in taken] == [abandoned.id]
    assert (taken[0].status, taken[0].runner_id, taken[0].check_count) == (
        DiagnosisStatus.QUEUED,
        new_owner,
        0,
    )
    checks = await diagnoses.list_checks(
        project_id=project.id, diagnosis_id=abandoned.id, limit=10, after=None
    )
    assert checks == []
    await session.refresh(replay_run)
    assert replay_run.check_id is None


async def test_a_released_diagnosis_is_taken_over_at_once(
    session: AsyncSession, project: Project
) -> None:
    diagnoses = DiagnosesRepository(session)
    run = await _run(session, project)
    diagnosis = await diagnoses.create(project_id=project.id, run_id=run.id, created_by_id=None)
    old_owner, now = uuid4(), utc_now()
    await diagnoses.claim(
        project_id=project.id, diagnosis_id=diagnosis.id, runner_id=old_owner, now=now
    )

    await diagnoses.release(runner_id=old_owner)
    taken = await diagnoses.take_over_abandoned(
        stale_before=now - ABANDONED_AFTER,
        created_after=now - timedelta(hours=1),
        runner_id=uuid4(),
        now=now,
    )

    assert [d.id for d in taken] == [diagnosis.id]
