"""flag(): mark a run that passed as failed, for a failure its success check could not see."""

from uuid import UUID

from first_domino._generated.models import FlagRunRequest, Run
from first_domino.client import MAX_REASON_CHARS, FirstDominoClient, default_client


async def flag(run_id: UUID, reason: str, *, client: FirstDominoClient | None = None) -> Run:
    """Mark a finished recorded run that passed as failed, and diagnose it.

    Use it when a user complains (a thumbs-down, a support ticket) about a run your check
    let pass. Keep `fd.current_run_id()` next to the conversation to know which run.
    Replays of a flagged run are judged by a model against `reason`. A reason longer
    than 2000 characters is cut.

    Raises:
        ValueError: `reason` is empty.
        ConfigurationError: `FIRST_DOMINO_API_KEY` is not set.
        ApiRequestError: The API refused: `not_found` for an unknown run, `conflict` when
            the run is not a finished recorded run that passed.

    Example:
        >>> run = await fd.flag(run_id, "The user said the refund went to the wrong card")
        >>> run.status
        <RunStatus.failed: 'failed'>
    """
    api = client or default_client()
    request = FlagRunRequest(run_id=run_id, reason=reason[:MAX_REASON_CHARS])
    return await api.flag_run(request)
