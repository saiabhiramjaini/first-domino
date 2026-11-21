"""RunReader port over the runs and steps repositories."""

from uuid import UUID

from fd_database.repositories import RunsRepository, StepsRepository
from fd_database.session import Database
from fd_shared.errors import NotFoundError
from fd_shared.models import RunView, StepView


class DatabaseRunReader:
    """Reads one project's runs and steps for the engine."""

    def __init__(self, database: Database, project_id: UUID) -> None:
        self._database = database
        self._project_id = project_id

    async def get_run(self, run_id: UUID) -> RunView:
        """The run, its task input and its step count.

        Raises:
            NotFoundError: The project has no such run.
        """
        async with self._database.transaction() as session:
            run = await RunsRepository(session).get(project_id=self._project_id, run_id=run_id)
        if run is None:
            raise NotFoundError
        return RunView(
            id=run.id,
            agent_name=run.agent_name,
            task_input=run.task_input,
            tool_names=run.tool_names,
            status=run.status,
            step_count=run.step_count,
            final_output=run.final_output,
            failure_reason=run.failure_reason,
            flagged=run.flagged_at is not None,
        )

    async def get_steps(self, run_id: UUID) -> list[StepView]:
        """The run's steps in index order."""
        async with self._database.transaction() as session:
            steps = await StepsRepository(session).list_all(
                project_id=self._project_id, run_id=run_id
            )
        return [
            StepView(
                index=step.index,
                model=step.model,
                output=step.output,
                tool_results=step.tool_results,
            )
            for step in steps
        ]
