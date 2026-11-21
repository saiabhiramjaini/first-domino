"""Record one fresh call for the live demo and print the web link to watch it.

It returns as soon as the call is recorded. A failed call is diagnosed by First Domino
while the running worker (`make worker`) replays it, so the presenter opens the link and
watches the search narrow.

Usage, from `server/`:
    uv run python -m fd_demo_agent.demo_live --bug b02
    uv run python -m fd_demo_agent.demo_live --clean
"""

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass
from uuid import UUID

import first_domino as fd
from fd_demo_agent.agent import CallAgent
from fd_demo_agent.bugs import PlantedBug, get_bug
from fd_demo_agent.llm import OpenAIChatModel, openai_client
from fd_demo_agent.recording import RecordedCall, run_recorded
from fd_demo_agent.runner import BugNotReachedError
from fd_demo_agent.settings import DemoAgentSettings
from fd_demo_agent.tasks import CallTask, get_task

DEFAULT_BUG = "b02"
CLEAN_TASK = "t07"
EXIT_OK = 0
EXIT_NOT_RECORDED = 1
EXIT_RERUN = 2

log = logging.getLogger("fd_demo_agent")


@dataclass(frozen=True, slots=True)
class DemoCall:
    """Which call to record: a planted bug on its own call, or a clean call."""

    task: CallTask
    bug: PlantedBug | None


def demo_call(bug_id: str | None) -> DemoCall:
    """Return the call for a bug id, or the clean demo call when `bug_id` is None.

    Raises:
        KeyError: No bug has this id.
    """
    if bug_id is None:
        return DemoCall(task=get_task(CLEAN_TASK), bug=None)
    bug = get_bug(bug_id)
    return DemoCall(task=get_task(bug.task_id), bug=bug)


def run_url(web_url: str, run_id: UUID) -> str:
    """Return the web app page of a run."""
    return f"{web_url.rstrip('/')}/runs/{run_id}"


def _report(call: DemoCall, recorded: RecordedCall, url: str) -> int:
    report = recorded.run.report
    label = call.bug.bug_id if call.bug else "clean"
    if report.passed and call.bug is not None:
        log.warning(
            "demo.bug_recovered bug=%s url=%s (the model recovered; nothing to diagnose, "
            "run it again)",
            label,
            url,
        )
        return EXIT_RERUN
    if report.passed:
        log.info("demo.call_passed task=%s url=%s", call.task.task_id, url)
    else:
        log.info(
            "demo.call_failed task=%s bug=%s reason=%s url=%s (diagnosis starting; open the link)",
            call.task.task_id,
            label,
            report.failure,
            url,
        )
    return EXIT_OK


async def _record(call: DemoCall) -> int:
    settings = DemoAgentSettings()  # pyright: ignore[reportCallIssue] model is read from the environment
    client = fd.FirstDominoClient()
    if not client.enabled:
        log.error("demo.no_api_key (set FIRST_DOMINO_API_KEY in server/.env)")
        return EXIT_NOT_RECORDED
    agent = CallAgent(OpenAIChatModel(openai_client(settings)), settings)
    try:
        recorded = await run_recorded(agent, call.task, bug=call.bug, client=client)
    except BugNotReachedError:
        log.warning("demo.bug_not_reached bug=%s (run it again)", call.bug)
        return EXIT_RERUN
    finally:
        await client.aclose()
    if recorded.run_id is None:
        log.error("demo.not_recorded (is the API running at FIRST_DOMINO_BASE_URL?)")
        return EXIT_NOT_RECORDED
    return _report(call, recorded, run_url(settings.web_url, recorded.run_id))


def main() -> None:
    """Parse arguments, record one call and exit with 0, 1 (not recorded) or 2 (rerun)."""
    parser = argparse.ArgumentParser(description="Record one call for the live demo.")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--bug", default=DEFAULT_BUG, help="planted bug id, default b02")
    choice.add_argument("--clean", action="store_true", help="record a passing call instead")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    call = demo_call(None if args.clean else args.bug)
    sys.exit(asyncio.run(_record(call)))


if __name__ == "__main__":
    main()
