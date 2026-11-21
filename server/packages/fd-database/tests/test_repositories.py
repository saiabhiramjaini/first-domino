"""Repository behavior that the API relies on: idempotence, the job queue and tenancy."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.repositories import (
    ApiKeysRepository,
    DiagnosesRepository,
    ReplayJobsRepository,
    RunsRepository,
    StepsRepository,
)
from fd_database.tables import Project, ReplayJob, Run
from fd_database.tables.base import utc_now
from fd_shared.enums import (
    CheckPhase,
    CheckResult,
    MessageRole,
    ReplayJobStatus,
    ReplayOutcome,
)
from fd_shared.models import Message, TaskInput

MESSAGE = Message(role=MessageRole.ASSISTANT, content="hello")


async def _run(session: AsyncSession, project: Project) -> Run:
    api_key = await ApiKeysRepository(session).create(
        project_id=project.id,
        name="k",
        prefix="fd_live_abcd",
        key_hash=uuid4().hex * 2,
        created_by_id=project.owner_id,
    )
    return await RunsRepository(session).create(
        project_id=project.id,
        agent_name="call-assistant",
        task_input=TaskInput(prompt="Call the clinic and add tomorrow at 10 to the calendar"),
        tool_names=["add_calendar_event"],
        created_by_id=api_key.id,
        started_at=utc_now(),
    )


async def _record(session: AsyncSession, project: Project, run: Run, content: str):
    return await StepsRepository(session).record(
        project_id=project.id,
        run_id=run.id,
        index=1,
        model="m",
        output=Message(role=MessageRole.ASSISTANT, content=content),
        tool_results=[],
        messages=[MESSAGE],
        tokens_in=1,
        tokens_out=1,
        latency_ms=1,
    )


async def test_recording_a_step_twice_keeps_the_first(
    session: AsyncSession, project: Project
) -> None:
    run = await _run(session, project)

    first = await _record(session, project, run, "first")
    second = await _record(session, project, run, "second")

    assert second.id == first.id
    assert second.output.content == "first"
    assert second.messages == [MESSAGE]


async def test_rows_of_another_project_are_not_found(
    session: AsyncSession, project: Project, other_project: Project
) -> None:
    run = await _run(session, project)

    assert await RunsRepository(session).get(project_id=other_project.id, run_id=run.id) is None


async def _enqueue(session: AsyncSession, project: Project, run: Run, samples: int):
    return await ReplayJobsRepository(session).enqueue(
        project_id=project.id,
        run_id=run.id,
        diagnosis_id=None,
        check_id=None,
        agent_name=run.agent_name,
        task_input=run.task_input,
        from_step=0,
        messages=[MESSAGE],
        replacement_output=None,
        model_override=None,
        samples=samples,
    )


async def test_expired_lease_requeues_then_expires_after_max_attempts(
    session: AsyncSession, project: Project
) -> None:
    jobs = ReplayJobsRepository(session)
    run = await _run(session, project)
    [job] = await _enqueue(session, project, run, samples=1)
    now = utc_now()

    for attempt in (1, 2):
        leased = await jobs.lease_next(
            project_id=project.id,
            agent_names=["call-assistant"],
            leased_by_id=run.created_by_id,
            now=now,
            lease_seconds=10,
        )
        assert leased is not None
        assert leased.attempt == attempt
        now += timedelta(seconds=11)
        await jobs.expire_leases(project_id=project.id, now=now, max_attempts=2)

    stored = await jobs.get(project_id=project.id, replay_job_id=job.id, refresh=True)
    assert stored is not None
    assert stored.status is ReplayJobStatus.EXPIRED


async def test_lease_only_hands_out_jobs_for_the_named_agents(
    session: AsyncSession, project: Project
) -> None:
    run = await _run(session, project)
    await _enqueue(session, project, run, samples=1)

    leased = await ReplayJobsRepository(session).lease_next(
        project_id=project.id,
        agent_names=["someone-else"],
        leased_by_id=run.created_by_id,
        now=utc_now(),
        lease_seconds=10,
    )

    assert leased is None


async def test_submit_counts_only_the_first_result(session: AsyncSession, project: Project) -> None:
    jobs = ReplayJobsRepository(session)
    run = await _run(session, project)
    [job] = await _enqueue(session, project, run, samples=1)
    await jobs.lease_next(
        project_id=project.id,
        agent_names=["call-assistant"],
        leased_by_id=run.created_by_id,
        now=utc_now(),
        lease_seconds=10,
    )

    async def submit(outcome: ReplayOutcome):
        return await jobs.submit(
            project_id=project.id,
            replay_job_id=job.id,
            outcome=outcome,
            replay_run_id=None,
            error_code=None,
            now=utc_now(),
        )

    first = await submit(ReplayOutcome.PASSED)
    repeat = await submit(ReplayOutcome.FAILED)

    assert first is not None
    assert repeat is not None
    assert repeat.outcome is ReplayOutcome.PASSED
    assert repeat.status is ReplayJobStatus.SUCCEEDED


async def test_one_active_diagnosis_per_run(session: AsyncSession, project: Project) -> None:
    diagnoses = DiagnosesRepository(session)
    run = await _run(session, project)
    await diagnoses.create(project_id=project.id, run_id=run.id, created_by_id=None)

    assert await diagnoses.has_active(project_id=project.id, run_id=run.id)
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await diagnoses.create(project_id=project.id, run_id=run.id, created_by_id=None)


async def test_saving_a_check_again_updates_it(session: AsyncSession, project: Project) -> None:
    diagnoses = DiagnosesRepository(session)
    run = await _run(session, project)
    diagnosis = await diagnoses.create(project_id=project.id, run_id=run.id, created_by_id=None)

    for passes, result in ((0, CheckResult.PENDING), (2, CheckResult.CAN_SUCCEED)):
        await diagnoses.save_check(
            project_id=project.id,
            diagnosis_id=diagnosis.id,
            index=0,
            phase=CheckPhase.PRECHECK,
            save_point=0,
            samples=3,
            passes=passes,
            result=result,
            finished_at=None,
        )

    checks = await diagnoses.list_checks(
        project_id=project.id, diagnosis_id=diagnosis.id, limit=10, after=None
    )
    assert [(check.passes, check.result) for check in checks] == [(2, CheckResult.CAN_SUCCEED)]


async def test_waiting_replays_count_only_jobs_no_worker_picked_up(
    session: AsyncSession, project: Project
) -> None:
    jobs = ReplayJobsRepository(session)
    run = await _run(session, project)
    diagnosis = await DiagnosesRepository(session).create(
        project_id=project.id, run_id=run.id, created_by_id=None
    )
    await jobs.enqueue(
        project_id=project.id,
        run_id=run.id,
        diagnosis_id=diagnosis.id,
        check_id=None,
        agent_name=run.agent_name,
        task_input=run.task_input,
        from_step=0,
        messages=[MESSAGE],
        replacement_output=None,
        model_override=None,
        samples=3,
    )
    await jobs.lease_next(
        project_id=project.id,
        agent_names=["call-assistant"],
        leased_by_id=run.created_by_id,
        now=utc_now(),
        lease_seconds=10,
    )

    waiting = await jobs.waiting_by_diagnosis(project_id=project.id, diagnosis_ids=[diagnosis.id])

    assert waiting[diagnosis.id].count == 2
    assert await jobs.waiting_by_diagnosis(project_id=project.id, diagnosis_ids=[]) == {}


async def test_restarted_diagnoses_end_their_unfinished_replays(
    session: AsyncSession, project: Project
) -> None:
    jobs = ReplayJobsRepository(session)
    run = await _run(session, project)
    diagnosis = await DiagnosesRepository(session).create(
        project_id=project.id, run_id=run.id, created_by_id=None
    )
    queued = await jobs.enqueue(
        project_id=project.id,
        run_id=run.id,
        diagnosis_id=diagnosis.id,
        check_id=None,
        agent_name=run.agent_name,
        task_input=run.task_input,
        from_step=0,
        messages=[MESSAGE],
        replacement_output=None,
        model_override=None,
        samples=2,
    )

    await jobs.expire_for_diagnoses(diagnosis_ids=[diagnosis.id], now=utc_now())

    for job in queued:
        stored = await jobs.get(project_id=project.id, replay_job_id=job.id, refresh=True)
        assert stored is not None
        assert stored.status is ReplayJobStatus.EXPIRED


async def test_expire_unfinished_ends_queued_and_leased_jobs_only(
    session: AsyncSession, project: Project
) -> None:
    jobs = ReplayJobsRepository(session)
    run = await _run(session, project)

    async def lease() -> ReplayJob:
        leased = await jobs.lease_next(
            project_id=project.id,
            agent_names=["call-assistant"],
            leased_by_id=run.created_by_id,
            now=utc_now(),
            lease_seconds=10,
        )
        assert leased is not None
        return leased

    [finished] = await _enqueue(session, project, run, samples=1)
    await lease()
    await jobs.submit(
        project_id=project.id,
        replay_job_id=finished.id,
        outcome=ReplayOutcome.PASSED,
        replay_run_id=None,
        error_code=None,
        now=utc_now(),
    )
    first, second = await _enqueue(session, project, run, samples=2)
    started = await lease()
    waiting = second if started.id == first.id else first

    ended = await jobs.expire_unfinished(
        project_id=project.id,
        replay_job_ids=[started.id, waiting.id, finished.id],
        now=utc_now(),
    )

    statuses = {
        job.id: (await jobs.get(project_id=project.id, replay_job_id=job.id, refresh=True)).status  # type: ignore[union-attr]
        for job in (started, waiting, finished)
    }
    assert ended == 2
    assert statuses == {
        started.id: ReplayJobStatus.EXPIRED,
        waiting.id: ReplayJobStatus.EXPIRED,
        finished.id: ReplayJobStatus.SUCCEEDED,
    }
