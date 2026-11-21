"""The message list at a save point of a recorded run."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from fd_database import tables
from fd_database.repositories import StepsRepository
from fd_shared.enums import MessageRole
from fd_shared.models import Message


def opening_messages(step: tables.Step) -> list[Message]:
    """The messages before step 1: its snapshot without its own output and tool results."""
    added = 1 + len(step.tool_results)
    return list(step.messages[:-added])


async def messages_after(
    session: AsyncSession, *, project_id: UUID, run: tables.Run, save_point: int
) -> list[Message]:
    """The messages after steps 1 to `save_point` (0 means before step 1)."""
    steps = StepsRepository(session)
    index = max(save_point, 1)
    step = await steps.get_by_index(project_id=project_id, run_id=run.id, index=index)
    if step is None:
        return [Message(role=MessageRole.USER, content=run.task_input.prompt)]
    return list(step.messages) if save_point > 0 else opening_messages(step)
