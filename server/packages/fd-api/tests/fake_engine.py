"""A real engine with canned model calls, so API tests make no network calls."""

from fd_engine.diagnose import Diagnoser
from fd_engine.explain import ExplainedStep
from fd_engine.group import CauseCandidate, CauseMatch
from fd_engine.judge import JudgedReplay
from fd_engine.ports import CheckSink, ReplayRunner, RunReader
from fd_engine.settings import EngineSettings
from fd_engine.verify import FixedStep
from fd_shared.enums import CauseCategory, MessageRole, ReplayOutcome
from fd_shared.models import Explanation, Message, RunView, StepView

FIXED_OUTPUT = Message(role=MessageRole.ASSISTANT, content="fixed")
GOOD_FINAL_OUTPUT = "Did what the user asked"
"""The final output of a replay the canned judge passes; any other output fails."""
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


class FinalOutputJudge:
    """Passes a replay whose run finished with `GOOD_FINAL_OUTPUT`, whatever the worker said."""

    async def judge(
        self, run: RunView, replay: RunView, replay_steps: list[StepView]
    ) -> JudgedReplay:
        passed = replay.final_output == GOOD_FINAL_OUTPUT
        outcome = ReplayOutcome.PASSED if passed else ReplayOutcome.FAILED
        return JudgedReplay(outcome=outcome, reason="canned", cost_usd=0.003)


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
            judge=FinalOutputJudge(),
            settings=self.settings,
        )

    def matcher(self) -> FirstCauseMatch:
        return FirstCauseMatch()
