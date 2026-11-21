"""Record one fresh call for the live demo and print the web link to watch it.

It returns as soon as the call is recorded. A failed call is diagnosed by First Domino
while the running worker (`make worker`) replays it, so the presenter opens the link and
watches the search narrow. Every outcome is one plain sentence for the presenter, never a
traceback.

Usage, from `server/`:
    make demo-live BUG=b02
    make demo-live-clean
"""

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass
from uuid import UUID

import openai
from pydantic import ValidationError

import first_domino as fd
from fd_demo_agent.agent import CallAgent
from fd_demo_agent.bugs import PLANTED_BUGS, PlantedBug, get_bug
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

log = logging.getLogger("fd_demo_agent.demo_live")


@dataclass(frozen=True, slots=True)
class DemoCall:
    """Which call to record: a planted bug on its own call, or a clean call."""

    task: CallTask
    bug: PlantedBug | None


@dataclass(frozen=True, slots=True)
class DemoOutcome:
    """What to tell the presenter, and the exit code."""

    message: str
    exit_code: int


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


def describe(call: DemoCall, recorded: RecordedCall, web_url: str) -> DemoOutcome:
    """Turn a recorded call into the one line the presenter sees."""
    if recorded.run_id is None:
        return DemoOutcome(
            "Not recorded: is the API running at FIRST_DOMINO_BASE_URL?", EXIT_NOT_RECORDED
        )
    url = run_url(web_url, recorded.run_id)
    report = recorded.run.report
    if call.bug is None:
        verdict = "passed" if report.passed else f"failed on its own ({report.failure})"
        return DemoOutcome(f"Clean call {verdict}: {url}", EXIT_OK)
    if report.passed:
        return DemoOutcome(
            f"The agent recovered from {call.bug.bug_id} this time, so there is nothing to "
            f"diagnose. Run it again. ({url})",
            EXIT_RERUN,
        )
    return DemoOutcome(
        f"Call failed ({report.failure}); First Domino is diagnosing it. Watch: {url}", EXIT_OK
    )


async def _record(call: DemoCall, settings: DemoAgentSettings) -> DemoOutcome:
    client = fd.FirstDominoClient()
    if not client.enabled:
        return DemoOutcome("Set FIRST_DOMINO_API_KEY in server/.env first.", EXIT_NOT_RECORDED)
    agent = CallAgent(OpenAIChatModel(openai_client(settings)), settings)
    try:
        recorded = await run_recorded(agent, call.task, bug=call.bug, client=client)
    except BugNotReachedError:
        return DemoOutcome("The agent finished before the planted step. Run it again.", EXIT_RERUN)
    except openai.APIError as exc:
        return DemoOutcome(f"The model call failed ({type(exc).__name__}).", EXIT_NOT_RECORDED)
    finally:
        await client.aclose()
    return describe(call, recorded, settings.web_url)


def _settings() -> DemoAgentSettings | DemoOutcome:
    try:
        settings = DemoAgentSettings()  # pyright: ignore[reportCallIssue] model is read from the environment
    except ValidationError:
        return DemoOutcome("Set FD_DEMO_AGENT_MODEL in server/.env first.", EXIT_NOT_RECORDED)
    if settings.openai_api_key is None:
        return DemoOutcome("Set OPENAI_API_KEY in server/.env first.", EXIT_NOT_RECORDED)
    return settings


def _run(bug_id: str | None) -> DemoOutcome:
    try:
        call = demo_call(bug_id)
    except KeyError:
        known = ", ".join(bug.bug_id for bug in PLANTED_BUGS)
        return DemoOutcome(f"Unknown bug {bug_id}. Pick one of {known}.", EXIT_NOT_RECORDED)
    settings = _settings()
    if isinstance(settings, DemoOutcome):
        return settings
    return asyncio.run(_record(call, settings))


def main() -> None:
    """Record one call, print one line, exit 0, 1 (not recorded) or 2 (run it again)."""
    parser = argparse.ArgumentParser(description="Record one call for the live demo.")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--bug", default=DEFAULT_BUG, help="planted bug id, default b02")
    choice.add_argument("--clean", action="store_true", help="record a passing call instead")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    log.setLevel(logging.INFO)
    outcome = _run(None if args.clean else args.bug)
    log.log(logging.INFO if outcome.exit_code == EXIT_OK else logging.WARNING, outcome.message)
    sys.exit(outcome.exit_code)


if __name__ == "__main__":
    main()
