"""A real engine with canned model calls, so API tests make no network calls."""

from fd_engine.diagnose import Diagnoser
from fd_engine.explain import ExplainedStep
from fd_engine.group import CauseCandidate, CauseMatch
from fd_engine.ports import CheckSink, ReplayRunner, RunReader
from fd_engine.settings import EngineSettings
from fd_engine.verify import FixedStep
from fd_shared.enums import CauseCategory, MessageRole
from fd_shared.models import Explanation, Message, RunView, StepView

FIXED_OUTPUT = Message(role=MessageRole.ASSISTANT, content="fixed")
EXPLANATION = Explanation(
    title="Event added on the wrong day",
    summary="The assistant turned 'tomorrow at 10' into the day after tomorrow.",
    suggested_fix="Resolve relative dates against the call's date.",
    category=CauseCategory.WRONG_DATE,
)


class CannedFixer:
    async def fix(self, run: RunView, steps: list[StepView], step_index: int) -> FixedStep:
        return FixedStep(output=FIXED_OUTPUT, cost_usd=0.001)


class CannedExplainer:
    async def explain(
        self, run: RunView, steps: list[StepView], step: int, fixed_output: Message | None
    ) -> ExplainedStep:
        return ExplainedStep(explanation=EXPLANATION, cost_usd=0.002)


class FirstCauseMatch:
    """Files every cause under the first existing group."""

    async def match(
        self, explanation: Explanation, candidates: list[CauseCandidate], *, step_name: str
    ) -> CauseMatch:
        return CauseMatch(cause_id=candidates[0].id if candidates else None, cost_usd=0.0)


class FakeEngine:
    """The real `Diagnoser` over the API's adapters, with fixed model answers."""

    settings = EngineSettings.model_validate(
        {
            "strong_model": "test-strong-model",
            "samples_per_check": 1,
            "verify_samples": 2,
            "verify_pass_threshold": 2,
            "fallback_window": 1,
            "replay_timeout_seconds": 20.0,
        }
    )

    def diagnoser(self, *, reader: RunReader, runner: ReplayRunner, sink: CheckSink) -> Diagnoser:
        return Diagnoser(
            reader=reader,
            runner=runner,
            sink=sink,
            fixer=CannedFixer(),
            explainer=CannedExplainer(),
            settings=self.settings,
        )

    def matcher(self) -> FirstCauseMatch:
        return FirstCauseMatch()
