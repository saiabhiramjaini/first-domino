"""Renders a run's steps as plain text for the fixer, the explainer and the baseline judge."""

from fd_engine.models import Message, RunView, StepView


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
    """The task the agent was given, with its metadata."""
    lines = [f"# Task for agent {run.agent_name}", run.task_input.prompt]
    lines.extend(f"{key}: {value}" for key, value in sorted(run.task_input.metadata.items()))
    if run.tool_names:
        lines.append(f"Tools the agent can call: {', '.join(run.tool_names)}")
    return "\n".join(lines)


def render_steps(steps: list[StepView]) -> str:
    """Every step in order, separated by blank lines."""
    return "\n\n".join(render_step(step) for step in steps)
