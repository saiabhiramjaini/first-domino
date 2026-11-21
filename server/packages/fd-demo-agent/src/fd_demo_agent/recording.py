"""Record the call assistant's runs through the public First Domino SDK, like any customer."""

import logging
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from openai.types.chat import ChatCompletionAssistantMessageParam

import first_domino as fd
from fd_demo_agent.agent import AgentStep, CallAgent, StepCallback
from fd_demo_agent.bugs import PlantedBug
from fd_demo_agent.prompts import opening_messages
from fd_demo_agent.runner import TaskRun, run_task
from fd_demo_agent.tasks import CallTask
from fd_demo_agent.toolbox import ToolName
from fd_demo_agent.world import load_world

AGENT_NAME = "call-assistant"
TASK_ID_KEY = "task_id"
BUG_ID_KEY = "bug_id"
PLANTED_STEP_KEY = "planted_step"

log = logging.getLogger("fd_demo_agent")


def task_input_for(task: CallTask, bug: PlantedBug | None = None) -> fd.TaskInput:
    """Describe a call for First Domino: the incoming call text, plus ids in metadata.

    A planted bug's id and step go in the metadata, so the benchmark knows the true step.
    """
    opening = opening_messages(task, load_world().user)[-1]
    metadata = {TASK_ID_KEY: task.task_id}
    if bug is not None:
        metadata |= {BUG_ID_KEY: bug.bug_id, PLANTED_STEP_KEY: str(bug.step)}
    return fd.TaskInput(prompt=str(opening.get("content")), metadata=metadata)


def task_id_of(task_input: fd.TaskInput) -> str:
    """Return the call id a task input carries.

    Raises:
        KeyError: The metadata has no task id.
    """
    return (task_input.metadata or {})[TASK_ID_KEY]


def record_steps(run: fd.RecordedRun) -> StepCallback:
    """Return an `on_step` callback that records each agent step into `run`."""

    async def record(step: AgentStep) -> None:
        await run.step(
            index=step.index,
            model=step.model,
            output=fd.message_from_openai(step.output),
            tool_results=[fd.message_from_openai(m) for m in step.tool_results],
            messages=[fd.message_from_openai(m) for m in step.messages],
            tokens_in=step.tokens_in,
            tokens_out=step.tokens_out,
            latency_ms=step.latency_ms,
        )

    return record


def assistant_output(message: fd.Message) -> ChatCompletionAssistantMessageParam:
    """Convert a replay job's replacement output into the agent's message format.

    Raises:
        ValueError: The message is not an assistant turn.
    """
    if message.role != fd.MessageRole.assistant:
        msg = f"a replacement output must be an assistant message, not {message.role}"
        raise ValueError(msg)
    return cast(ChatCompletionAssistantMessageParam, fd.message_to_openai(message))


@dataclass(frozen=True, slots=True)
class RecordedCall:
    """A call run and the id First Domino gave it, or None when recording was off."""

    run_id: UUID | None
    run: TaskRun


async def run_recorded(
    agent: CallAgent,
    task: CallTask,
    *,
    bug: PlantedBug | None = None,
    on_step: StepCallback | None = None,
    client: fd.FirstDominoClient | None = None,
) -> RecordedCall:
    """Run a call, record it through the SDK and finish it as passed or failed.

    Recording is dark without `FIRST_DOMINO_API_KEY`; the run itself is the same.
    """
    task_input = task_input_for(task, bug)
    tool_names = [name.value for name in ToolName]
    async with fd.record(AGENT_NAME, task_input, tool_names=tool_names, client=client) as run:
        save = record_steps(run)

        async def each_step(step: AgentStep) -> None:
            await save(step)
            if on_step is not None:
                await on_step(step)

        result = await run_task(agent, task, bug=bug, on_step=each_step)
        status = fd.RunOutcome.passed if result.report.passed else fd.RunOutcome.failed
        await run.finish(status, final_output=result.final_output)
    log.info("agent.run_recorded task=%s run_id=%s", task.task_id, run.run_id)
    return RecordedCall(run_id=run.run_id, run=result)
