"""Builds the engine for one diagnosis: the diagnoser over the adapters and the cause grouper."""

from functools import cached_property
from typing import Protocol

from fd_engine.diagnose import Diagnoser
from fd_engine.group import CauseCandidate, CauseGrouper, CauseMatch
from fd_engine.llm import Llm
from fd_engine.ports import CheckSink, ReplayRunner, RunReader
from fd_engine.settings import EngineSettings
from fd_shared.models import Explanation


class CauseMatcher(Protocol):
    """Matches a new explanation to an existing cause group."""

    async def match(
        self, explanation: Explanation, candidates: list[CauseCandidate], *, step_name: str
    ) -> CauseMatch: ...


class EngineFactory(Protocol):
    """What the diagnosis runner needs from the engine."""

    def diagnoser(self, *, reader: RunReader, runner: ReplayRunner, sink: CheckSink) -> Diagnoser:
        """A diagnoser that works through these adapters."""
        ...

    def matcher(self) -> CauseMatcher:
        """The cause grouper."""
        ...


class LlmEngineFactory:
    """The real engine, with one shared model client per process.

    Settings and the client are built on first use, so the API starts even when the engine is
    not configured; a diagnosis then fails with the engine's error code.
    """

    def __init__(self, settings: EngineSettings | None = None) -> None:
        self._given_settings = settings

    @cached_property
    def _settings(self) -> EngineSettings:
        return self._given_settings or EngineSettings()  # pyright: ignore[reportCallIssue] fields come from the environment

    @cached_property
    def _llm(self) -> Llm:
        return Llm(self._settings)

    def diagnoser(self, *, reader: RunReader, runner: ReplayRunner, sink: CheckSink) -> Diagnoser:
        """A diagnoser whose fixer and explainer use the shared model client."""
        return Diagnoser.with_llm(
            self._llm, reader=reader, runner=runner, sink=sink, settings=self._settings
        )

    def matcher(self) -> CauseMatcher:
        """The cause grouper over the shared model client."""
        return CauseGrouper(self._llm)
