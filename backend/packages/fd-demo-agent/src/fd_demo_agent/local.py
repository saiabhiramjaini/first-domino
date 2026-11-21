"""Run demo calls locally against OpenAI and log each step and verdict.

Usage, from `backend/`:
    uv run python -m fd_demo_agent.local --task t01
    uv run python -m fd_demo_agent.local --task t01 --bug b02
    uv run python -m fd_demo_agent.local --all
"""

import argparse
import asyncio
import logging

from fd_demo_agent.agent import AgentStep, CallAgent
from fd_demo_agent.bugs import PLANTED_BUGS, PlantedBug, get_bug
from fd_demo_agent.llm import OpenAIChatModel, openai_client
from fd_demo_agent.messages import function_calls, text_of
from fd_demo_agent.runner import TaskRun, run_task
from fd_demo_agent.settings import DemoAgentSettings
from fd_demo_agent.tasks import TASKS, CallTask, get_task

log = logging.getLogger("fd_demo_agent")


async def _log_step(step: AgentStep) -> None:
    calls = [
        f"{call['function']['name']}({call['function']['arguments']})"
        for call in function_calls(step.output)
    ]
    log.info(
        "agent.step index=%d text=%r calls=%s results=%s",
        step.index,
        text_of(step.output),
        calls,
        [result["content"] for result in step.tool_results],
    )


def _log_run(run: TaskRun) -> None:
    log.info(
        "agent.run_finished task=%s bug=%s passed=%s failure=%s steps=%d outcome=%s",
        run.task.task_id,
        run.bug.bug_id if run.bug else None,
        run.report.passed,
        run.report.failure,
        len(run.steps),
        run.outcome.model_dump_json(),
    )


def _plan(args: argparse.Namespace) -> list[tuple[CallTask, PlantedBug | None]]:
    if args.all:
        clean: list[tuple[CallTask, PlantedBug | None]] = [(task, None) for task in TASKS]
        return clean + [(get_task(bug.task_id), bug) for bug in PLANTED_BUGS]
    if args.bug:
        bug = get_bug(args.bug)
        return [(get_task(bug.task_id), bug)]
    return [(get_task(args.task), None)]


async def _main(args: argparse.Namespace) -> None:
    settings = DemoAgentSettings()  # pyright: ignore[reportCallIssue] model is read from the environment
    agent = CallAgent(OpenAIChatModel(openai_client(settings)), settings)
    for task, bug in _plan(args):
        log.info("agent.run_started task=%s bug=%s", task.task_id, bug.bug_id if bug else None)
        _log_run(await run_task(agent, task, bug=bug, on_step=_log_step))


def main() -> None:
    """Parse arguments and run the chosen tasks."""
    parser = argparse.ArgumentParser(description="Run demo calls locally and log each step.")
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--task", help="call id, such as t01")
    choice.add_argument("--bug", help="planted bug id, such as b02; runs its call")
    choice.add_argument("--all", action="store_true", help="every call, then every bug")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(_main(parser.parse_args()))


if __name__ == "__main__":
    main()
