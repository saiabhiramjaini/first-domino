"""Diagnoses and checks repository."""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.pages import IndexKey, TimeKey
from fd_database.tables import Check, Diagnosis
from fd_database.tables.base import utc_now
from fd_database.tables.diagnoses import ACTIVE_DIAGNOSIS_STATUSES
from fd_shared.enums import CheckPhase, CheckResult, DiagnosisStatus, VerdictKind
from fd_shared.models import Explanation, Message


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
        diagnosis.finished_at = finished_at
        await self._session.flush()
        return diagnosis

    async def fail(
        self, *, diagnosis: Diagnosis, error_code: str, finished_at: datetime
    ) -> Diagnosis:
        """Moves the diagnosis to `failed` with a stable error code."""
        diagnosis.status = DiagnosisStatus.FAILED
        diagnosis.error_code = error_code
        diagnosis.finished_at = finished_at
        await self._session.flush()
        return diagnosis

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
    ) -> list[Diagnosis]:
        """A page of matching diagnoses, newest first."""
        conditions = _filters(project_id, run_ids, cause_ids, statuses, verdict_kinds)
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
    ) -> int:
        """The number of matching diagnoses."""
        conditions = _filters(project_id, run_ids, cause_ids, statuses, verdict_kinds)
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
) -> list[ColumnElement[bool]]:
    conditions = [Diagnosis.project_id == project_id]
    if run_ids is not None:
        conditions.append(Diagnosis.run_id.in_(run_ids))
    if cause_ids is not None:
        conditions.append(Diagnosis.cause_id.in_(cause_ids))
    if statuses is not None:
        conditions.append(Diagnosis.status.in_(statuses))
    if verdict_kinds is not None:
        conditions.append(Diagnosis.verdict_kind.in_(verdict_kinds))
    return conditions
