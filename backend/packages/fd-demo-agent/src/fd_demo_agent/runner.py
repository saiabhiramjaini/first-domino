"""Run one demo task end to end, optionally with a planted bug, and check the result."""

from dataclasses import dataclass

from fd_demo_agent.agent import AgentStep, BookingAgent, StepCallback, StopReason
from fd_demo_agent.bugs import PlantedBug
from fd_demo_agent.messages import assistant_messages
from fd_demo_agent.prompts import opening_messages
from fd_demo_agent.sandbox import Booking
from fd_demo_agent.success import SuccessReport, check_booking
from fd_demo_agent.tasks import DemoTask
from fd_demo_agent.world import load_world


class BugNotReachedError(Exception):
    """The run ended before the step a planted bug overwrites."""


@dataclass(frozen=True, slots=True)
class TaskRun:
    """A finished task run: every step, the booking it left and the success verdict."""

    task: DemoTask
    bug: PlantedBug | None
    steps: list[AgentStep]
    final_output: str | None
    booking: Booking | None
    report: SuccessReport


async def run_task(
    agent: BookingAgent,
    task: DemoTask,
    *,
    bug: PlantedBug | None = None,
    on_step: StepCallback | None = None,
) -> TaskRun:
    """Run a task from its opening messages and check the booking.

    With a bug, the model writes steps before `bug.step`, the bug's replacement becomes
    that step, and the model continues from there: the same mechanism a replay uses.

    Raises:
        BugNotReachedError: The model finished before the bug's step.
    """
    messages = opening_messages(task.prompt, load_world().calendar.today)
    steps: list[AgentStep] = []
    replacement = None
    if bug is not None:
        before = await agent.run(messages, step_limit=bug.step - 1, on_step=on_step)
        reached = len(assistant_messages(before.messages)) == bug.step - 1
        if before.stop_reason != StopReason.STEP_LIMIT or not reached:
            msg = f"run of {task.task_id} ended before step {bug.step} of bug {bug.bug_id}"
            raise BugNotReachedError(msg)
        messages, steps, replacement = before.messages, before.steps, bug.replacement
    result = await agent.run(messages, replacement_output=replacement, on_step=on_step)
    return TaskRun(
        task=task,
        bug=bug,
        steps=[*steps, *result.steps],
        final_output=result.final_output,
        booking=result.booking,
        report=check_booking(task, result.booking),
    )
