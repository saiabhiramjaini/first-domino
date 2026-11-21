"""Build labelled failed runs by planting bugs into successful runs.

For each call that has planted bugs, run it cleanly a few times. In every clean run that
passed, overwrite the bug's step with the bug's output, let the agent continue, and keep the
run when the success check fails and every one of `doom_samples` replays from the planted step
fails too. The planted step is then the first doomed step: the clean run shows the steps before
it can succeed, and the replays show the run cannot recover after it.

Usage, from `server/`:
    uv run python -m fd_scripts.make_dataset
    uv run python -m fd_scripts.make_dataset --runs-per-task 1 --bugs b01,b06 --name trial
"""

import asyncio
from collections.abc import Awaitable, Iterable
from datetime import UTC, datetime
from uuid import uuid4

import click
from openai import OpenAIError
from openai.types.chat import ChatCompletionMessageParam

from fd_demo_agent.agent import CallAgent
from fd_demo_agent.bugs import PLANTED_BUGS, PlantedBug
from fd_demo_agent.llm import OpenAIChatModel, openai_client
from fd_demo_agent.prompts import opening_messages
from fd_demo_agent.runner import TaskRun, run_task
from fd_demo_agent.settings import DemoAgentSettings
from fd_demo_agent.success import check_call
from fd_demo_agent.tasks import CallTask, get_task
from fd_demo_agent.toolbox import ToolName
from fd_demo_agent.world import load_world
from fd_scripts.convert import step_view
from fd_scripts.dataset import Dataset, LabelledRun, save_dataset
from fd_scripts.settings import ScriptsSettings
from fd_shared.enums import RunStatus
from fd_shared.logging import configure_logging, get_logger
from fd_shared.models import RunView, TaskInput

log = get_logger(__name__)


async def _bounded[T](limit: asyncio.Semaphore, work: Awaitable[T]) -> T:
    async with limit:
        return await work


async def _clean_run(agent: CallAgent, task_id: str) -> TaskRun | None:
    try:
        run = await run_task(agent, get_task(task_id))
    except OpenAIError as error:
        log.warning("dataset.clean_run_failed", task_id=task_id, error=type(error).__name__)
        return None
    log.info("dataset.clean_run", task_id=task_id, passed=run.report.passed, steps=len(run.steps))
    return run if run.report.passed else None


def _call_prompt(clean: TaskRun) -> str:
    """The incoming-call message the agent started from, as the run's task prompt."""
    user_turn = opening_messages(clean.task, load_world().user)[-1]
    content = user_turn.get("content")
    return content if isinstance(content, str) else clean.task.title


async def _doomed(
    agent: CallAgent, task: CallTask, start: list[ChatCompletionMessageParam], samples: int
) -> bool:
    """True when every replay from `start` fails the call's success check."""
    try:
        results = await asyncio.gather(*(agent.run(task, start) for _ in range(samples)))
    except OpenAIError:
        return False
    return not any(check_call(task, result.outcome).passed for result in results)


async def _plant(
    agent: CallAgent, clean: TaskRun, bug: PlantedBug, case_id: str, doom_samples: int
) -> LabelledRun | None:
    """Replay `clean` up to the bug's step, plant the bug and continue; keep it if doomed."""
    if len(clean.steps) < bug.step:
        return None
    prefix = clean.steps[: bug.step - 1]
    task = clean.task
    start = prefix[-1].messages if prefix else opening_messages(task, load_world().user)
    try:
        result = await agent.run(task, start, replacement_output=bug.replacement)
    except OpenAIError as error:
        log.warning("dataset.plant_failed", case_id=case_id, error=type(error).__name__)
        return None
    report = check_call(task, result.outcome)
    doomed = report.failure is not None and await _doomed(
        agent, task, result.steps[0].messages, doom_samples
    )
    log.info("dataset.planted", case_id=case_id, failure=report.failure, doomed=doomed)
    if report.failure is None or not doomed:
        return None
    steps = [step_view(step) for step in [*prefix, *result.steps]]
    return LabelledRun(
        case_id=case_id,
        task_id=task.task_id,
        bug_id=bug.bug_id,
        bug_kind=bug.kind,
        true_step=bug.step,
        failure=report.failure,
        run=RunView(
            id=uuid4(),
            agent_name="call-assistant",
            task_input=TaskInput(prompt=_call_prompt(clean), metadata={"task_id": task.task_id}),
            status=RunStatus.FAILED,
            step_count=len(steps),
            final_output=result.final_output,
            tool_names=[tool.value for tool in ToolName],
        ),
        steps=steps,
    )


async def build(
    agent: CallAgent, bugs: Iterable[PlantedBug], settings: ScriptsSettings, runs_per_task: int
) -> list[LabelledRun]:
    """Return every planted run that is doomed, over `runs_per_task` clean runs of each call."""
    bugs = list(bugs)
    limit = asyncio.Semaphore(settings.dataset_concurrency)
    task_ids = sorted({bug.task_id for bug in bugs})
    clean_runs = await asyncio.gather(
        *(
            _bounded(limit, _clean_run(agent, task_id))
            for task_id in task_ids
            for _ in range(runs_per_task)
        )
    )
    plants = [
        _bounded(limit, _plant(agent, clean, bug, f"{bug.bug_id}-r{number}", settings.doom_samples))
        for number, clean in enumerate(clean_runs)
        if clean is not None
        for bug in bugs
        if bug.task_id == clean.task.task_id
    ]
    return [case for case in await asyncio.gather(*plants) if case is not None]


async def _main(runs_per_task: int | None, bug_ids: list[str], name: str) -> None:
    scripts = ScriptsSettings()
    agent_settings = DemoAgentSettings()  # pyright: ignore[reportCallIssue] model is read from the environment
    agent = CallAgent(OpenAIChatModel(openai_client(agent_settings)), agent_settings)
    bugs = [bug for bug in PLANTED_BUGS if not bug_ids or bug.bug_id in bug_ids]
    cases = await build(agent, bugs, scripts, runs_per_task or scripts.clean_runs_per_task)
    dataset = Dataset(created_at=datetime.now(UTC), agent_model=agent_settings.model, cases=cases)
    path = scripts.datasets_dir / f"{name}.json"
    save_dataset(dataset, path)
    print(f"{len(cases)} labelled failed runs written to {path}")
    for kind in sorted({case.bug_kind for case in cases}):
        print(f"  {kind}: {sum(case.bug_kind == kind for case in cases)}")


@click.command()
@click.option("--runs-per-task", type=int, default=None, help="Clean runs per call.")
@click.option("--bugs", default="", help="Comma-separated bug ids; all bugs when empty.")
@click.option("--name", default="call-assistant", help="Dataset file name, without .json.")
def main(runs_per_task: int | None, bugs: str, name: str) -> None:
    """Build the labelled dataset of failed call-assistant runs."""
    configure_logging()
    asyncio.run(_main(runs_per_task, [bug for bug in bugs.split(",") if bug], name))


if __name__ == "__main__":
    main()
