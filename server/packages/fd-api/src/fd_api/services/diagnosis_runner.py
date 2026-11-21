"""Registry that runs diagnoses as tracked background tasks."""

import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

import httpx
from fastapi import Request

from fd_api.adapters.check_sink import DatabaseCheckSink
from fd_api.adapters.check_tracker import CheckTracker
from fd_api.adapters.replay_runner import QueueReplayRunner
from fd_api.adapters.run_reader import DatabaseRunReader
from fd_api.services.engine import EngineFactory
from fd_api.services.slack import new_cause_message, send_slack_message
from fd_api.services.verdicts import store_verdict
from fd_api.settings import ApiSettings
from fd_database import tables
from fd_database.repositories import DiagnosesRepository, ProjectsRepository
from fd_database.session import Database
from fd_database.tables.base import utc_now
from fd_shared.enums import DiagnosisErrorCode
from fd_shared.errors import FirstDominoError
from fd_shared.logging import get_logger

log = get_logger(__name__)


def diagnosis_error_code(error: FirstDominoError) -> DiagnosisErrorCode:
    """The stored code for an error that stopped a diagnosis. Unknown codes are internal."""
    try:
        return DiagnosisErrorCode(error.code)
    except ValueError:
        return DiagnosisErrorCode.INTERNAL_ERROR


class DiagnosisRunner:
    """Runs each diagnosis in a background task and holds it until it ends.

    Several API processes may share one database. Each runner has its own `runner_id`, claims
    the diagnoses it runs and refreshes their heartbeat; a runner fails only diagnoses whose
    owner stopped heartbeating, never another live process's.
    """

    def __init__(
        self,
        database: Database,
        engine: EngineFactory,
        http: httpx.AsyncClient,
        settings: ApiSettings,
    ) -> None:
        self._database = database
        self._engine = engine
        self._http = http
        self._settings = settings
        self._tasks: set[asyncio.Task[None]] = set()
        self._keep_alive: asyncio.Task[None] | None = None
        self.runner_id = uuid4()

    async def start(self, *, project_id: UUID, run_id: UUID, diagnosis_id: UUID) -> None:
        """Starts a committed, `queued` diagnosis in the background and returns at once.

        Async so FastAPI runs it on the event loop, not in its thread pool.
        """
        task = asyncio.create_task(
            self._run(project_id=project_id, run_id=run_id, diagnosis_id=diagnosis_id),
            name=f"diagnosis-{diagnosis_id}",
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def open(self) -> None:
        """Fails abandoned diagnoses, then keeps this runner's heartbeat going. Call at startup."""
        await self.fail_abandoned()
        self._keep_alive = asyncio.create_task(
            self._heartbeat_forever(), name="diagnosis-heartbeat"
        )

    async def fail_abandoned(self) -> None:
        """Fails unfinished diagnoses whose owning process stopped heartbeating."""
        now = utc_now()
        stale_before = now - timedelta(seconds=self._settings.diagnosis_abandoned_after_seconds)
        async with self._database.transaction() as session:
            count = await DiagnosesRepository(session).fail_abandoned(
                stale_before=stale_before,
                error_code=DiagnosisErrorCode.INTERRUPTED,
                finished_at=now,
            )
        if count:
            log.warning("diagnoses.interrupted", count=count)

    async def heartbeat(self) -> None:
        """Marks this runner's diagnoses as still running."""
        async with self._database.transaction() as session:
            await DiagnosesRepository(session).heartbeat(runner_id=self.runner_id, now=utc_now())

    async def shutdown(self) -> None:
        """Stops the heartbeat, cancels running diagnoses and waits for them to stop."""
        tasks = [*self._tasks, *([self._keep_alive] if self._keep_alive else [])]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def wait_idle(self) -> None:
        """Waits until no diagnosis is running."""
        while self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _heartbeat_forever(self) -> None:
        while True:
            await asyncio.sleep(self._settings.diagnosis_heartbeat_seconds)
            try:
                await self.heartbeat()
                await self.fail_abandoned()
            except Exception:
                log.exception("diagnoses.heartbeat_failed")

    async def _claim(self, project_id: UUID, diagnosis_id: UUID) -> bool:
        async with self._database.transaction() as session:
            return await DiagnosesRepository(session).claim(
                project_id=project_id,
                diagnosis_id=diagnosis_id,
                runner_id=self.runner_id,
                now=utc_now(),
            )

    async def _run(self, *, project_id: UUID, run_id: UUID, diagnosis_id: UUID) -> None:
        if not await self._claim(project_id, diagnosis_id):
            log.warning("diagnoses.not_claimed", diagnosis_id=str(diagnosis_id))
            return
        try:
            await self._diagnose(project_id=project_id, run_id=run_id, diagnosis_id=diagnosis_id)
        except FirstDominoError as error:
            await self._fail(project_id, diagnosis_id, diagnosis_error_code(error))
        except Exception:
            log.exception("diagnoses.crashed", diagnosis_id=str(diagnosis_id))
            await self._fail(project_id, diagnosis_id, DiagnosisErrorCode.INTERNAL_ERROR)

    async def _diagnose(self, *, project_id: UUID, run_id: UUID, diagnosis_id: UUID) -> None:
        tracker = CheckTracker()
        diagnoser = self._engine.diagnoser(
            reader=DatabaseRunReader(self._database, project_id),
            runner=QueueReplayRunner(
                self._database,
                project_id=project_id,
                diagnosis_id=diagnosis_id,
                tracker=tracker,
                settings=self._settings,
            ),
            sink=DatabaseCheckSink(self._database, project_id, tracker),
        )
        result = await diagnoser.diagnose(run_id, diagnosis_id)
        stored = await store_verdict(
            self._database,
            self._engine.matcher(),
            project_id=project_id,
            diagnosis_id=diagnosis_id,
            result=result,
        )
        if stored.cause is not None and stored.cause_is_new:
            await self._announce(project_id, stored.cause)

    async def _announce(self, project_id: UUID, cause: tables.Cause) -> None:
        async with self._database.transaction() as session:
            project = await ProjectsRepository(session).get(project_id=project_id)
        if project is None or project.slack_webhook_url is None:
            return
        await send_slack_message(
            self._http,
            project.slack_webhook_url,
            new_cause_message(cause, web_app_url=self._settings.web_app_url),
            timeout_seconds=self._settings.slack_timeout_seconds,
        )

    async def _fail(
        self, project_id: UUID, diagnosis_id: UUID, error_code: DiagnosisErrorCode
    ) -> None:
        async with self._database.transaction() as session:
            diagnoses = DiagnosesRepository(session)
            diagnosis = await diagnoses.get(project_id=project_id, diagnosis_id=diagnosis_id)
            if diagnosis is not None:
                await diagnoses.fail(
                    diagnosis=diagnosis, error_code=error_code, finished_at=utc_now()
                )
        log.warning("diagnoses.failed", diagnosis_id=str(diagnosis_id), error_code=error_code)


def get_diagnosis_runner(request: Request) -> DiagnosisRunner:
    """The process's diagnosis runner, set up at startup."""
    return request.app.state.diagnosis_runner
