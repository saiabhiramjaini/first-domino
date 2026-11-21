"""C3 end to end: record a failed run, auto-diagnose it, replay on a fake worker, store the verdict.

The worker is a stand-in for the SDK's: it talks to the real API over HTTP. Its "agent" is
doomed when it keeps the recorded step 2 (the wrong calendar date) and succeeds otherwise,
or when it is handed the fixed step.
"""

import asyncio
from typing import Any

from httpx import AsyncClient

from .conftest import Headers

AGENT = "call-assistant"
DOOMED_STEP = 2
TASK = {"prompt": "Clinic call: book tomorrow at 10", "metadata": {"task_id": "e2e"}}
TOOLS = ["get_caller_details", "add_calendar_event", "send_confirmation"]
DEADLINE_SECONDS = 30.0


def _step(run_id: str, index: int, tool: str) -> dict[str, Any]:
    call = {"id": f"call_{index}", "name": tool, "arguments": "{}"}
    output = {"role": "assistant", "content": None, "tool_calls": [call]}
    result = {"role": "tool", "content": "ok", "tool_call_id": f"call_{index}"}
    opening = [
        {"role": "system", "content": "You are a call assistant."},
        {"role": "user", "content": TASK["prompt"]},
    ]
    return {
        "run_id": run_id,
        "index": index,
        "model": "agent-model",
        "output": output,
        "tool_results": [result],
        "messages": opening + [output, result] * index,
        "tokens_in": 100,
        "tokens_out": 20,
        "latency_ms": 300,
    }


async def _record_failed_run(client: AsyncClient, api_key: Headers) -> str:
    started = await client.post(
        "/v1/runs.start",
        json={"agent_name": AGENT, "task_input": TASK, "tool_names": TOOLS},
        headers=api_key,
    )
    run_id = started.json()["run"]["id"]
    for index, tool in enumerate(TOOLS, start=1):
        await client.post("/v1/steps.record", json=_step(run_id, index, tool), headers=api_key)
    await client.post(
        "/v1/runs.finish",
        json={"run_id": run_id, "status": "failed", "final_output": "Booked the wrong day"},
        headers=api_key,
    )
    return run_id


def _replay_outcome(job: dict[str, Any]) -> str:
    if job["replacement_output"] is not None:
        return "passed"
    return "failed" if job["from_step"] >= DOOMED_STEP else "passed"


async def _work_one(client: AsyncClient, api_key: Headers, job: dict[str, Any]) -> None:
    started = await client.post(
        "/v1/runs.start",
        json={"agent_name": AGENT, "task_input": job["task_input"], "replay_job_id": job["id"]},
        headers=api_key,
    )
    replay_run_id = started.json()["run"]["id"]
    outcome = _replay_outcome(job)
    await client.post(
        "/v1/runs.finish", json={"run_id": replay_run_id, "status": outcome}, headers=api_key
    )
    await client.post(
        "/v1/replay-jobs.submit",
        json={"replay_job_id": job["id"], "outcome": outcome, "replay_run_id": replay_run_id},
        headers=api_key,
    )


async def _work_until_done(
    client: AsyncClient, api_key: Headers, person: Headers, diagnosis_id: str
) -> dict[str, Any]:
    async with asyncio.timeout(DEADLINE_SECONDS):
        while True:
            diagnosis = (
                await client.get(
                    "/v1/diagnoses.get", params={"diagnosis_id": diagnosis_id}, headers=person
                )
            ).json()["diagnosis"]
            if diagnosis["status"] in {"done", "failed"}:
                return diagnosis
            leased = await client.post(
                "/v1/replay-jobs.lease",
                json={"agent_names": [AGENT], "wait_seconds": 0},
                headers=api_key,
            )
            job = leased.json()["replay_job"]
            if job is None:
                await asyncio.sleep(0.05)
            else:
                await _work_one(client, api_key, job)


async def test_failed_run_is_diagnosed_and_proven_by_replay(
    client: AsyncClient, person: Headers, api_key: Headers
) -> None:
    run_id = await _record_failed_run(client, api_key)
    run = (await client.get("/v1/runs.get", params={"run_id": run_id}, headers=person)).json()

    diagnosis_id = run["run"]["latest_diagnosis_id"]
    diagnosis = await _work_until_done(client, api_key, person, diagnosis_id)

    assert diagnosis["status"] == "done", diagnosis
    assert diagnosis["verdict_kind"] == "step_verified"
    assert diagnosis["first_domino_step"] == DOOMED_STEP
    assert diagnosis["verify_passes"] == diagnosis["verify_samples"] == 2
    assert diagnosis["explanation"]["category"] == "wrong_date"

    checks = await client.post(
        "/v1/checks.list", json={"diagnosis_id": diagnosis["id"]}, headers=person
    )
    phases = [check["phase"] for check in checks.json()["items"]]
    assert phases[0] == "calibrate"
    assert phases[1:4] == ["bisect", "bisect", "precheck"], "a doomed save point is rechecked"
    assert phases[-1] == "verify"
    assert all(check["finished_at"] is not None for check in checks.json()["items"])

    cause = await client.get(
        "/v1/causes.get", params={"cause_id": diagnosis["cause_id"]}, headers=person
    )
    assert cause.json()["cause"]["step_name"] == "add_calendar_event"
    assert cause.json()["cause"]["verified_count"] == 1

    replays = await client.post("/v1/runs.count", json={"sources": ["replay"]}, headers=person)
    assert replays.json()["count"] == diagnosis["replay_count"]


async def test_each_check_lists_its_replays_and_the_cause_exports_as_tests(
    client: AsyncClient, person: Headers, api_key: Headers
) -> None:
    run_id = await _record_failed_run(client, api_key)
    run = (await client.get("/v1/runs.get", params={"run_id": run_id}, headers=person)).json()
    diagnosis = await _work_until_done(client, api_key, person, run["run"]["latest_diagnosis_id"])
    checks = (
        await client.post("/v1/checks.list", json={"diagnosis_id": diagnosis["id"]}, headers=person)
    ).json()["items"]

    for check in checks:
        replays = (
            await client.post("/v1/runs.list", json={"check_id": check["id"]}, headers=person)
        ).json()["items"]
        counted = await client.post(
            "/v1/runs.count", json={"check_id": check["id"]}, headers=person
        )
        assert len(replays) == check["samples"] == counted.json()["count"]
        assert {replay["check_id"] for replay in replays} == {check["id"]}
        assert {replay["parent_run_id"] for replay in replays} == {run_id}
        assert [r["started_at"] for r in replays] == sorted(r["started_at"] for r in replays)

    exported = await client.post(
        "/v1/causes.export", json={"cause_id": diagnosis["cause_id"]}, headers=person
    )
    [case] = exported.json()["export"]["cases"]
    assert case["run_id"] == run_id
    assert case["first_domino_step"] == DOOMED_STEP
    assert case["original_output"]["tool_calls"][0]["name"] == TOOLS[DOOMED_STEP - 1]
    assert [m["role"] for m in case["messages"]] == ["system", "user", "assistant", "tool"]
    assert case["fixed_output"]["content"] == "fixed"
    assert case["verified"] is True
