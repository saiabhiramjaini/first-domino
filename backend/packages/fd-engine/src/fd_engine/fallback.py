"""Rank and try nearby suspect steps when verify does not prove the found step."""

from pydantic import BaseModel, ConfigDict, Field

from fd_engine.checks import CheckRunner
from fd_engine.models import CheckPhase, RunView, StepView
from fd_engine.settings import EngineSettings
from fd_engine.verify import FixAttempt, Verifier


def rank_candidates(found: int, step_count: int, window: int) -> list[int]:
    """Return the steps within `window` of `found`, nearest first and earlier first on a tie."""
    ranked: list[int] = []
    for distance in range(1, window + 1):
        ranked.extend(
            step for step in (found - distance, found + distance) if 1 <= step <= step_count
        )
    return ranked


class FallbackOutcome(BaseModel):
    """Which nearby fix, if any, flipped the outcome, and how many were tried."""

    model_config = ConfigDict(frozen=True)

    verified: FixAttempt | None
    tried: int = Field(ge=0)
    cost_usd: float = Field(ge=0)


class Fallback:
    """Tries a fix on each nearby step until one is verified or the check budget runs out."""

    def __init__(
        self,
        *,
        checks: CheckRunner,
        verifier: Verifier,
        settings: EngineSettings,
    ) -> None:
        self._checks = checks
        self._verifier = verifier
        self._settings = settings

    async def search(self, run: RunView, steps: list[StepView], found: int) -> FallbackOutcome:
        """Try fixes on the steps around `found` and return the first that is verified."""
        tried = 0
        cost_usd = 0.0
        for step in rank_candidates(found, len(steps), self._settings.fallback_window):
            if self._checks.remaining <= 0:
                break
            attempt = await self._verifier.try_fix(run, steps, step, CheckPhase.FALLBACK)
            cost_usd += attempt.cost_usd
            if attempt.passes is None:
                continue
            tried += 1
            if attempt.verified:
                return FallbackOutcome(verified=attempt, tried=tried, cost_usd=cost_usd)
        return FallbackOutcome(verified=None, tried=tried, cost_usd=cost_usd)
