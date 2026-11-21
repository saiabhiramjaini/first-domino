"""Diagnoses and checks repository."""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ColumnElement, delete, exists, func, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.pages import IndexKey, TimeKey
from fd_database.tables import Check, Diagnosis, ReplayJob, Run
from fd_database.tables.base import utc_now
from fd_database.tables.diagnoses import ACTIVE_DIAGNOSIS_STATUSES
from fd_shared.enums import (
    CheckPhase,
    CheckResult,
    DiagnosisErrorCode,
    DiagnosisStatus,
    VerdictKind,
)
from fd_shared.models import Explanation, Message

RELEASED_AT = datetime(2000, 1, 1, tzinfo=UTC)
"""The heartbeat of a diagnosis whose process stopped on purpose: abandoned at once."""


class DetachedCause(BaseModel):
    """A cause group that one detached diagnosis was counted in."""

    model_config = ConfigDict(frozen=True)

    cause_id: UUID
    verified: bool


class DiagnosesRepository:
    """Diagnoses and the checks inside them."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_active(self, *, project_id: UUID, run_id: UUID) -> bool:
        """Whether a diagnosis of the run is still running."""
        statement = select(
            exists().where(
                Diagnosis.project_id == project_id,
                Diagnosis.run_id == run_id,
                Diagnosis.status.in_(ACTIVE_DIAGNOSIS_STATUSES),
            )
        )
        return bool(await self._session.scalar(statement))

    async def create(
        self, *, project_id: UUID, run_id: UUID, created_by_id: UUID | None
    ) -> Diagnosis:
        """Creates a `queued` diagnosis. The database allows one active diagnosis per run."""
        diagnosis = Diagnosis(
            project_id=project_id,
            run_id=run_id,
            status=DiagnosisStatus.QUEUED,
            check_count=0,
            replay_count=0,
            cost_usd=Decimal(0),
            created_by_id=created_by_id,
        )
        self._session.add(diagnosis)
        await self._session.flush()
        return diagnosis

    async def get(self, *, project_id: UUID, diagnosis_id: UUID) -> Diagnosis | None:
        """One diagnosis of the project, freshly read."""
        statement = (
            select(Diagnosis)
            .where(Diagnosis.project_id == project_id, Diagnosis.id == diagnosis_id)
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(statement)

    async def set_progress(
        self,
        *,
        diagnosis: Diagnosis,
        status: DiagnosisStatus,
        search_low: int | None,
        search_high: int | None,
    ) -> Diagnosis:
        """Stores the live status and search range."""
        diagnosis.status = status
        diagnosis.search_low = search_low
        diagnosis.search_high = search_high
        await self._session.flush()
        return diagnosis

    async def detach_earlier(
        self, *, project_id: UUID, run_id: UUID, keep_diagnosis_id: UUID
    ) -> list[DetachedCause]:
        """Takes the run's other diagnoses out of their cause groups.

        A run belongs to the cause of its latest diagnosis only, so a re-diagnosis never counts
        the same run in two groups. Returns what each detached diagnosis counted toward.
        """
        statement = (
            select(Diagnosis)
            .where(
                Diagnosis.project_id == project_id,
                Diagnosis.run_id == run_id,
                Diagnosis.id != keep_diagnosis_id,
                Diagnosis.cause_id.is_not(None),
            )
            .with_for_update()
        )
        detached: list[DetachedCause] = []
        for diagnosis in await self._session.scalars(statement):
            cause_id = diagnosis.cause_id
            if cause_id is None:
                continue
            verified = diagnosis.verdict_kind is VerdictKind.STEP_VERIFIED
            detached.append(DetachedCause(cause_id=cause_id, verified=verified))
            diagnosis.cause_id = None
        await self._session.flush()
        return detached

    async def count_progress(
        self, *, project_id: UUID, diagnosis_id: UUID, checks_at_least: int, replays_added: int
    ) -> None:
        """Keeps the live counts current while the engine runs. The verdict overwrites them."""
        await self._session.execute(
            update(Diagnosis)
            .where(Diagnosis.project_id == project_id, Diagnosis.id == diagnosis_id)
            .values(
                check_count=func.greatest(Diagnosis.check_count, checks_at_least),
                replay_count=Diagnosis.replay_count + replays_added,
            )
        )

    async def finish(
        self,
        *,
        diagnosis: Diagnosis,
        verdict_kind: VerdictKind,
        first_domino_step: int | None,
        verify_passes: int | None,
        verify_samples: int | None,
        fixed_output: Message | None,
        explanation: Explanation | None,
        cause_id: UUID | None,
        check_count: int,
        replay_count: int,
        cost_usd: Decimal,
        finished_at: datetime,
    ) -> Diagnosis:
        """Stores the engine's verdict and moves the diagnosis to `done`."""
        diagnosis.status = DiagnosisStatus.DONE
        diagnosis.verdict_kind = verdict_kind
        diagnosis.first_domino_step = first_domino_step
        diagnosis.verify_passes = verify_passes
        diagnosis.verify_samples = verify_samples
        diagnosis.fixed_output = fixed_output
        diagnosis.explanation = explanation
        diagnosis.cause_id = cause_id
        diagnosis.check_count = check_count
        diagnosis.replay_count = replay_count
        diagnosis.cost_usd = cost_usd
        diagnosis.error_code = None
        diagnosis.finished_at = finished_at
        await self._session.flush()
        return diagnosis

    async def fail(
        self, *, diagnosis: Diagnosis, error_code: DiagnosisErrorCode, finished_at: datetime
    ) -> Diagnosis:
        """Moves the diagnosis to `failed` with a stable error code."""
        diagnosis.status = DiagnosisStatus.FAILED
        diagnosis.error_code = error_code
        diagnosis.finished_at = finished_at
        await self._session.flush()
        return diagnosis

    async def claim(
        self, *, project_id: UUID, diagnosis_id: UUID, runner_id: UUID, now: datetime
    ) -> bool:
        """Marks an unfinished diagnosis as run by `runner_id`. False when it already ended."""
        claimed = await self._session.scalars(
            update(Diagnosis)
            .where(
                Diagnosis.project_id == project_id,
                Diagnosis.id == diagnosis_id,
                Diagnosis.status.in_(ACTIVE_DIAGNOSIS_STATUSES),
            )
            .values(runner_id=runner_id, heartbeat_at=now, updated_at=now)
            .returning(Diagnosis.id)
        )
        return claimed.one_or_none() is not None

    # The two writes below span projects on purpose: they belong to one API process (its
    # `runner_id`), or to no live process at all, never to a caller.

    async def heartbeat(self, *, runner_id: UUID, now: datetime) -> None:
        """Records that the process `runner_id` is still running its diagnoses."""
        await self._session.execute(
            update(Diagnosis)
            .where(
                Diagnosis.runner_id == runner_id,
                Diagnosis.status.in_(ACTIVE_DIAGNOSIS_STATUSES),
            )
            .values(heartbeat_at=now)
        )

    async def release(self, *, runner_id: UUID) -> None:
        """Gives up this process's unfinished diagnoses so the next process restarts them now."""
        await self._session.execute(
            update(Diagnosis)
            .where(
                Diagnosis.runner_id == runner_id,
                Diagnosis.status.in_(ACTIVE_DIAGNOSIS_STATUSES),
            )
            .values(heartbeat_at=RELEASED_AT)
        )

    async def take_over_abandoned(
        self, *, stale_before: datetime, created_after: datetime, runner_id: UUID, now: datetime
    ) -> list[Diagnosis]:
        """Claims unfinished diagnoses nobody runs any more, to restart them from the start.

        Only diagnoses created after `created_after` are taken, so one that keeps stopping
        its process is eventually failed by `fail_abandoned` instead of restarted forever.
        Their checks are deleted; the money already spent stays in `cost_usd`.
        """
        last_sign_of_life = func.coalesce(Diagnosis.heartbeat_at, Diagnosis.created_at)
        taken = list(
            await self._session.scalars(
                update(Diagnosis)
                .where(
                    Diagnosis.status.in_(ACTIVE_DIAGNOSIS_STATUSES),
                    last_sign_of_life < stale_before,
                    Diagnosis.created_at > created_after,
                )
                .values(
                    status=DiagnosisStatus.QUEUED,
                    runner_id=runner_id,
                    heartbeat_at=now,
                    search_low=None,
                    search_high=None,
                    check_count=0,
                    replay_count=0,
                    updated_at=now,
                )
                .returning(Diagnosis)
                .execution_options(populate_existing=True)
            )
        )
        if taken:
            old_checks = select(Check.id).where(Check.diagnosis_id.in_([d.id for d in taken]))
            for linked in (ReplayJob, Run):  # every table that points at a check
                await self._session.execute(
                    update(linked).where(linked.check_id.in_(old_checks)).values(check_id=None)
                )
            await self._session.execute(delete(Check).where(Check.id.in_(old_checks)))
        return taken

    async def fail_abandoned(
        self, *, stale_before: datetime, error_code: DiagnosisErrorCode, finished_at: datetime
    ) -> int:
        """Fails unfinished diagnoses nobody is running. Returns how many.

        Abandoned means the owner's last heartbeat, or the creation time of a diagnosis no
        process claimed, is older than `stale_before`.
        """
        last_sign_of_life = func.coalesce(Diagnosis.heartbeat_at, Diagnosis.created_at)
        failed = await self._session.scalars(
            update(Diagnosis)
            .where(
                Diagnosis.status.in_(ACTIVE_DIAGNOSIS_STATUSES),
                last_sign_of_life < stale_before,
            )
            .values(
                status=DiagnosisStatus.FAILED,
                error_code=error_code,
                finished_at=finished_at,
                updated_at=finished_at,
            )
            .returning(Diagnosis.id)
        )
        return len(failed.all())

    async def list_filtered(
        self,
        *,
        project_id: UUID,
        run_ids: Sequence[UUID] | None,
        cause_ids: Sequence[UUID] | None,
        statuses: Sequence[DiagnosisStatus] | None,
        verdict_kinds: Sequence[VerdictKind] | None,
        limit: int,
        after: TimeKey | None,
        latest_only: bool = False,
    ) -> list[Diagnosis]:
        """A page of matching diagnoses, newest first."""
        conditions = _filters(
            project_id, run_ids, cause_ids, statuses, verdict_kinds, latest_only=latest_only
        )
        statement = select(Diagnosis).where(*conditions)
        if after is not None:
            key = tuple_(Diagnosis.created_at, Diagnosis.id)
            statement = statement.where(key < (after.at, after.id))
        statement = statement.order_by(Diagnosis.created_at.desc(), Diagnosis.id.desc())
        return list(await self._session.scalars(statement.limit(limit)))

    async def count_filtered(
        self,
        *,
        project_id: UUID,
        run_ids: Sequence[UUID] | None,
        cause_ids: Sequence[UUID] | None,
        statuses: Sequence[DiagnosisStatus] | None,
        verdict_kinds: Sequence[VerdictKind] | None,
        latest_only: bool = False,
    ) -> int:
        """The number of matching diagnoses."""
        conditions = _filters(
            project_id, run_ids, cause_ids, statuses, verdict_kinds, latest_only=latest_only
        )
        statement = select(func.count()).select_from(Diagnosis).where(*conditions)
        return (await self._session.scalar(statement)) or 0

    async def save_check(
        self,
        *,
        project_id: UUID,
        diagnosis_id: UUID,
        index: int,
        phase: CheckPhase,
        save_point: int,
        samples: int,
        passes: int,
        drifted: int,
        drift_tool_name: str | None,
        result: CheckResult,
        finished_at: datetime | None,
    ) -> Check:
        """Creates the check at (`diagnosis_id`, `index`), or updates it if it exists."""
        now = utc_now()
        changes = {
            "phase": phase,
            "save_point": save_point,
            "samples": samples,
            "passes": passes,
            "drifted": drifted,
            "drift_tool_name": drift_tool_name,
            "result": result,
            "finished_at": finished_at,
            "updated_at": now,
        }
        statement = (
            insert(Check)
            .values(project_id=project_id, diagnosis_id=diagnosis_id, index=index, created_at=now)
            .values(**changes)
            .on_conflict_do_update(
                index_elements=[Check.project_id, Check.diagnosis_id, Check.index], set_=changes
            )
            .returning(Check)
            .execution_options(populate_existing=True)
        )
        return (await self._session.scalars(statement)).one()

    async def list_checks(
        self, *, project_id: UUID, diagnosis_id: UUID, limit: int, after: IndexKey | None
    ) -> list[Check]:
        """A page of a diagnosis's checks in index order."""
        statement = select(Check).where(
            Check.project_id == project_id, Check.diagnosis_id == diagnosis_id
        )
        if after is not None:
            statement = statement.where(Check.index > after.index)
        statement = statement.order_by(Check.index).limit(limit)
        return list(await self._session.scalars(statement))


def _filters(
    project_id: UUID,
    run_ids: Sequence[UUID] | None,
    cause_ids: Sequence[UUID] | None,
    statuses: Sequence[DiagnosisStatus] | None,
    verdict_kinds: Sequence[VerdictKind] | None,
    *,
    latest_only: bool,
) -> list[ColumnElement[bool]]:
    conditions = [Diagnosis.project_id == project_id]
    if latest_only:
        conditions.append(
            exists().where(Run.project_id == project_id, Run.latest_diagnosis_id == Diagnosis.id)
        )
    if run_ids is not None:
        conditions.append(Diagnosis.run_id.in_(run_ids))
    if cause_ids is not None:
        conditions.append(Diagnosis.cause_id.in_(cause_ids))
    if statuses is not None:
        conditions.append(Diagnosis.status.in_(statuses))
    if verdict_kinds is not None:
        conditions.append(Diagnosis.verdict_kind.in_(verdict_kinds))
    return conditions
