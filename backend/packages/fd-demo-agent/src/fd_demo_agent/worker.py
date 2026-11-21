"""Entry point for the demo customer's replay worker: replays the call assistant on request.

Usage, from `backend/`:
    make worker
"""

import asyncio
import logging

import first_domino as fd
from fd_demo_agent.agent import AgentResult, CallAgent
from fd_demo_agent.llm import OpenAIChatModel, openai_client
from fd_demo_agent.recording import AGENT_NAME, assistant_output, record_steps, task_id_of
from fd_demo_agent.settings import DemoAgentSettings
from fd_demo_agent.success import check_call
from fd_demo_agent.tasks import get_task


def build_worker(agent: CallAgent, *, client: fd.FirstDominoClient | None = None) -> fd.Worker:
    """Return a worker that replays `agent` and judges replays with the success check.

    Example:
        >>> await build_worker(agent).run()
    """
    worker = fd.Worker(agent_names=[AGENT_NAME], client=client)

    @worker.agent(AGENT_NAME)
    async def replay(ctx: fd.ReplayContext) -> AgentResult:
        replacement = ctx.replacement_output
        result = await agent.run(
            get_task(task_id_of(ctx.task_input)),
            fd.messages_to_openai(ctx.messages),
            replacement_output=assistant_output(replacement) if replacement else None,
            model_override=ctx.model_override,
            on_step=record_steps(ctx.run),
        )
        ctx.final_output = result.final_output
        return result

    @worker.success_check(AGENT_NAME)
    def check(task_input: fd.TaskInput, result: AgentResult) -> bool:
        return check_call(get_task(task_id_of(task_input)), result.outcome).passed

    return worker


async def _main() -> None:
    settings = DemoAgentSettings()  # pyright: ignore[reportCallIssue] model is read from the environment
    agent = CallAgent(OpenAIChatModel(openai_client(settings)), settings)
    await build_worker(agent).run()


def main() -> None:
    """Run the demo customer's replay worker until stopped."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(_main())


if __name__ == "__main__":
    main()
