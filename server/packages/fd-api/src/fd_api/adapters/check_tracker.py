"""Which check of one diagnosis is running, shared by its check sink and replay runner."""

from uuid import UUID


class CheckTracker:
    """Holds the id of the check the engine started last.

    The engine runs one check at a time per diagnosis (start, replay, finish), so the replays
    it asks for belong to the check started last. The tracker lives as long as one diagnosis.
    """

    def __init__(self) -> None:
        self.current_check_id: UUID | None = None
