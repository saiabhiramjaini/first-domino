"""The labelled dataset: failed call-assistant runs with the step that doomed them."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from fd_demo_agent.bugs import BugKind
from fd_demo_agent.success import FailureReason
from fd_shared.models import RunView, StepView


class LabelledRun(BaseModel):
    """A failed run and its label: the planted step is the first doomed step.

    The steps before `true_step` come from a run that passed, so the run can still succeed
    from them.
    """

    model_config = ConfigDict(frozen=True)

    case_id: str
    task_id: str
    bug_id: str
    bug_kind: BugKind
    true_step: int = Field(ge=1)
    failure: FailureReason
    run: RunView
    steps: list[StepView]


class Dataset(BaseModel):
    """Every labelled run built in one go, with the model that wrote them."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime
    agent_model: str
    cases: list[LabelledRun]


def save_dataset(dataset: Dataset, path: Path) -> None:
    """Write the dataset as JSON, creating the folder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dataset.model_dump_json(indent=2))


def load_dataset(path: Path) -> Dataset:
    """Read a dataset written by `save_dataset`."""
    return Dataset.model_validate_json(path.read_text())
