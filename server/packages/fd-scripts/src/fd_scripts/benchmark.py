"""Score First Domino and the baseline judge on the labelled runs.

Both methods see the same runs and use the same strong model (`FD_ENGINE_STRONG_MODEL`).
First Domino replays the demo agent in this process; its cost includes every replay's
tokens. Results go to `data/benchmarks/` and to the database for `getLatestBenchmark`.

Usage, from `server/`:
    uv run python -m fd_scripts.benchmark --limit 3 --no-db
    uv run python -m fd_scripts.benchmark
    uv run python -m fd_scripts.benchmark --from-report data/benchmarks/<file>.json
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4

import click
from pydantic import BaseModel, ConfigDict

from fd_database.repositories.benchmark import BenchmarkRepository, NewBenchmarkResult
from fd_database.session import Database
from fd_demo_agent.agent import CallAgent
from fd_demo_agent.llm import OpenAIChatModel, openai_client
from fd_demo_agent.settings import DemoAgentSettings
from fd_engine.baseline import BaselineJudge
from fd_engine.diagnose import Diagnoser
from fd_engine.llm import Llm
from fd_engine.settings import EngineSettings
from fd_scripts.dataset import LabelledRun, load_dataset
from fd_scripts.in_process import DatasetReader, DemoReplayRunner, DiscardingSink
from fd_scripts.scoring import ACCURACY_DEFINITION, CaseResult, MethodScore, score
from fd_scripts.settings import ScriptsSettings
from fd_shared.enums import BenchmarkMethod, VerdictKind
from fd_shared.errors import FirstDominoError
from fd_shared.logging import configure_logging, get_logger

log = get_logger(__name__)


class BenchmarkReport(BaseModel):
    """Everything one benchmark run measured."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime
    dataset: str
    agent_model: str
    strong_model: str
    accuracy_definition: str = ACCURACY_DEFINITION
    scores: list[MethodScore]
    results: list[CaseResult]


class Bench:
    """Runs both methods on each labelled run."""

    def __init__(self, cases: dict[UUID, LabelledRun], scripts: ScriptsSettings) -> None:
        self._engine_settings = EngineSettings()  # pyright: ignore[reportCallIssue] fields come from the environment
        agent_settings = DemoAgentSettings()  # pyright: ignore[reportCallIssue] fields come from the environment
        agent = CallAgent(OpenAIChatModel(openai_client(agent_settings)), agent_settings)
        self._llm = Llm(self._engine_settings)
        self._runner = DemoReplayRunner(
            agent,
            cases,
            asyncio.Semaphore(scripts.replay_concurrency),
            self._engine_settings,
            scripts,
        )
        self._diagnoser = Diagnoser.with_llm(
            self._llm,
            reader=DatasetReader(cases),
            runner=self._runner,
            sink=DiscardingSink(),
            settings=self._engine_settings,
        )

    @property
    def strong_model(self) -> str:
        """The model both methods judge with."""
        return self._engine_settings.strong_model

    async def first_domino(self, case: LabelledRun) -> CaseResult:
        """Diagnose the run by bisecting replays, then verify by a fixed replay."""
        started = perf_counter()
        try:
            result = await self._diagnoser.diagnose(case.run.id, uuid4())
        except FirstDominoError as error:
            return self._result(
                BenchmarkMethod.FIRST_DOMINO, case, started, cost_usd=0.0, error_code=error.code
            )
        return self._result(
            BenchmarkMethod.FIRST_DOMINO,
            case,
            started,
            predicted_step=result.first_domino_step,
            verdict_kind=result.verdict_kind,
            cost_usd=result.cost_usd,
        )

    async def baseline(self, case: LabelledRun) -> CaseResult:
        """Ask the judge to read the whole trace once and name the step."""
        started = perf_counter()
        prediction = await BaselineJudge(self._llm).predict(case.run, case.steps)
        return self._result(
            BenchmarkMethod.READ_TRACE_JUDGE,
            case,
            started,
            predicted_step=prediction.step,
            cost_usd=prediction.cost_usd,
        )

    def _result(
        self,
        method: BenchmarkMethod,
        case: LabelledRun,
        started: float,
        *,
        cost_usd: float,
        predicted_step: int | None = None,
        verdict_kind: VerdictKind | None = None,
        error_code: str | None = None,
    ) -> CaseResult:
        replays = self._runner.usage(case.run.id).cost_usd
        is_engine = method is BenchmarkMethod.FIRST_DOMINO
        return CaseResult(
            method=method,
            case_id=case.case_id,
            bug_kind=case.bug_kind,
            true_step=case.true_step,
            predicted_step=predicted_step,
            verified=verdict_kind is VerdictKind.STEP_VERIFIED if is_engine else None,
            verdict_kind=verdict_kind,
            error_code=error_code,
            cost_usd=cost_usd + (replays if is_engine else 0.0),
            seconds=perf_counter() - started,
            replays=self._runner.replays_run(case.run.id) if is_engine else None,
        )


async def _score_case(
    bench: Bench, case: LabelledRun, limit: asyncio.Semaphore
) -> list[CaseResult]:
    async with limit:
        results = [await bench.first_domino(case), await bench.baseline(case)]
    for result in results:
        log.info(
            "benchmark.case",
            case_id=result.case_id,
            method=result.method,
            true_step=result.true_step,
            predicted_step=result.predicted_step,
            verdict_kind=result.verdict_kind,
            cost_usd=round(result.cost_usd, 4),
        )
    return results


def stored_rows(results: list[CaseResult]) -> list[NewBenchmarkResult]:
    """The database rows for the results. A run with no step named keeps a null prediction,
    which the database scores count as a miss, as `score` does."""
    return [
        NewBenchmarkResult(
            method=result.method,
            case_id=result.case_id,
            true_step=result.true_step,
            predicted_step=result.predicted_step,
            verified=result.verified,
            cost_usd=Decimal(str(round(result.cost_usd, 6))),
            seconds=result.seconds,
        )
        for result in results
    ]


async def _store(results: list[CaseResult]) -> None:
    database = Database()
    try:
        await database.create_tables()
        async with database.transaction() as session:
            await BenchmarkRepository(session).create(results=stored_rows(results))
    finally:
        await database.dispose()


def _print_scores(scores: list[MethodScore]) -> None:
    header = ("method", "runs", "exact", "±1", "verified", "replays", "cost $", "secs")
    print(f"{header[0]:<18} " + " ".join(f"{name:>8}" for name in header[1:]))
    for s in scores:
        verified = "-" if s.verified_rate is None else f"{s.verified_rate:.0%}"
        replays = "-" if s.mean_replays is None else f"{s.mean_replays:.1f}"
        print(
            f"{s.method.value:<18} {s.runs_scored:>8} {s.exact_accuracy:>8.0%} "
            f"{s.within_one_accuracy:>8.0%} {verified:>8} {replays:>8} {s.mean_cost_usd:>8.4f} "
            f"{s.mean_seconds:>8.1f}"
        )
    print(ACCURACY_DEFINITION)


async def _main(dataset_name: str, limit: int | None, *, store: bool) -> None:
    scripts = ScriptsSettings()
    dataset = load_dataset(scripts.datasets_dir / f"{dataset_name}.json")
    chosen = dataset.cases[:limit] if limit else dataset.cases
    cases = {case.run.id: case for case in chosen}
    bench = Bench(cases, scripts)
    case_limit = asyncio.Semaphore(scripts.benchmark_concurrency)
    nested = await asyncio.gather(*(_score_case(bench, case, case_limit) for case in chosen))
    results = [result for pair in nested for result in pair]
    scores = [score(method, results) for method in BenchmarkMethod]
    report = BenchmarkReport(
        created_at=datetime.now(UTC),
        dataset=dataset_name,
        agent_model=dataset.agent_model,
        strong_model=bench.strong_model,
        scores=scores,
        results=results,
    )
    path = scripts.benchmarks_dir / f"benchmark-{report.created_at:%Y%m%dT%H%M%SZ}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2))
    _print_scores(scores)
    print(f"Report written to {path}")
    if store:
        await _store(results)
        print("Stored in the database.")


@click.command()
@click.option("--dataset", "dataset_name", default="call-assistant", help="Dataset name.")
@click.option("--limit", type=int, default=None, help="Score only the first N runs.")
@click.option("--db/--no-db", "store", default=True, help="Also store the results.")
@click.option(
    "--from-report",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Store this saved report in the database instead of running the benchmark.",
)
def main(dataset_name: str, limit: int | None, *, store: bool, from_report: Path | None) -> None:
    """Score First Domino and the read-the-trace judge on the labelled runs."""
    configure_logging()
    if from_report is not None:
        report = BenchmarkReport.model_validate_json(from_report.read_text())
        asyncio.run(_store(report.results))
        print(f"Stored {len(report.results)} results from {from_report} in the database.")
        return
    asyncio.run(_main(dataset_name, limit, store=store))


if __name__ == "__main__":
    main()
