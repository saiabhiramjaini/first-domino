from dataclasses import dataclass

import pytest

import first_domino as fd
from first_domino.client import FirstDominoClient
from first_domino.testing import FakeApi, make_job
from first_domino.worker import WorkerErrorCode

AGENT = "call-assistant"
REPLY = fd.Message(role=fd.MessageRole.assistant, content="Handled.")


@dataclass
class CallResult:
    summary_sent: bool


def worker_with(client: FirstDominoClient, *, passes: bool) -> fd.Worker:
    worker = fd.Worker(agent_names=[AGENT], client=client)

    @worker.agent(AGENT)
    async def replay(ctx: fd.ReplayContext) -> CallResult:
        await ctx.run.step(model=ctx.model_override or "small", output=REPLY, messages=ctx.messages)
        ctx.final_output = "Handled."
        return CallResult(summary_sent=passes)

    @worker.success_check(AGENT)
    def check(task_input: fd.TaskInput, result: CallResult) -> bool:
        assert task_input.metadata == {"task_id": "t01"}
        return result.summary_sent

    return worker


async def test_no_job_means_nothing_to_do(api: FakeApi, client: FirstDominoClient) -> None:
    assert await worker_with(client, passes=True).run_once() is None


@pytest.mark.parametrize(
    ("passes", "outcome"), [(True, fd.ReplayOutcome.passed), (False, fd.ReplayOutcome.failed)]
)
async def test_a_job_is_replayed_recorded_checked_and_submitted(
    api: FakeApi, client: FirstDominoClient, passes: bool, outcome: fd.ReplayOutcome
) -> None:
    job = make_job(from_step=2, model_override="strong")
    api.jobs = [job]

    assert await worker_with(client, passes=passes).run_once() == outcome

    (run,) = api.runs.values()
    assert run.replay_job_id == job.id
    assert [(s.index, s.model) for s in api.steps] == [(3, "strong")]
    assert [(f.status.value, f.final_output) for f in api.finished] == [(outcome.value, "Handled.")]
    (submitted,) = api.submitted
    assert (submitted.replay_job_id, submitted.outcome, submitted.replay_run_id) == (
        job.id,
        outcome,
        run.id,
    )
    assert submitted.error_code is None


async def test_a_crashing_agent_is_submitted_as_errored(
    api: FakeApi, client: FirstDominoClient
) -> None:
    api.jobs = [make_job()]
    worker = fd.Worker(agent_names=[AGENT], client=client)

    @worker.agent(AGENT)
    async def replay(ctx: fd.ReplayContext) -> None:
        raise RuntimeError("tool exploded")

    @worker.success_check(AGENT)
    async def check(task_input: fd.TaskInput, result: None) -> bool:
        return True

    assert await worker.run_once() == fd.ReplayOutcome.errored
    assert [f.status for f in api.finished] == [fd.RunOutcome.errored]
    assert api.submitted[0].error_code is not None
    assert api.submitted[0].error_code.root == WorkerErrorCode.AGENT_FAILED


async def test_a_job_whose_run_cannot_start_is_errored(
    api: FakeApi, client: FirstDominoClient
) -> None:
    api.jobs = [make_job()]
    api.fail_paths = {"runs.start": 500}

    assert await worker_with(client, passes=True).run_once() == fd.ReplayOutcome.errored
    assert api.submitted[0].replay_run_id is None


async def test_a_failed_submit_does_not_stop_the_worker(
    api: FakeApi, client: FirstDominoClient
) -> None:
    api.jobs = [make_job()]
    api.fail_paths = {"replay-jobs.submit": 503}

    assert await worker_with(client, passes=True).run_once() == fd.ReplayOutcome.passed


async def test_the_worker_refuses_to_start_without_a_key(dark_client: FirstDominoClient) -> None:
    with pytest.raises(fd.ConfigurationError):
        await worker_with(dark_client, passes=True).run()


async def test_the_worker_refuses_to_start_without_a_success_check(
    client: FirstDominoClient,
) -> None:
    worker = fd.Worker(agent_names=[AGENT], client=client)

    @worker.agent(AGENT)
    async def replay(ctx: fd.ReplayContext) -> None:
        return None

    with pytest.raises(fd.ConfigurationError):
        await worker.run()
