"""Renders a run's steps as plain text for the fixer, the explainer and the judge."""

from fd_shared.models import Message, RunView, StepView


def render_message(message: Message) -> str:
    """One message as text: its content, then one line per tool call."""
    lines = [message.content] if message.content else []
    lines.extend(f"call {call.name}({call.arguments})" for call in message.tool_calls)
    return "\n".join(lines) or "(empty)"


def render_step(step: StepView) -> str:
    """One step: the assistant turn and the tool results that followed it."""
    parts = [f"## Step {step.index}", "assistant:", render_message(step.output)]
    for result in step.tool_results:
        parts.extend(["tool result:", render_message(result)])
    return "\n".join(parts)


def render_task(run: RunView) -> str:
    """The task the agent was given, with its metadata and the reported failure when known."""
    lines = [f"# Task for agent {run.agent_name}", run.task_input.prompt]
    lines.extend(f"{key}: {value}" for key, value in sorted(run.task_input.metadata.items()))
    if run.failure_reason:
        lines.append(f"Reported failure: {run.failure_reason}")
    return "\n".join(lines)


def tools_seen(steps: list[StepView]) -> list[str]:
    """Names of the tools the agent called in the run, in first-use order."""
    names = (call.name for step in steps for call in step.output.tool_calls)
    return list(dict.fromkeys(names))


def render_steps(steps: list[StepView]) -> str:
    """Every step in order, separated by blank lines."""
    return "\n\n".join(render_step(step) for step in steps)
