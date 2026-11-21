"""ScriptsSettings: output locations and sizes for the dataset builder and the benchmark."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from fd_shared.settings import SettingsBase


class ScriptsSettings(SettingsBase):
    """Settings for `fd-scripts`, read from `FD_SCRIPTS_*`. Paths are relative to `backend/`."""

    model_config = SettingsConfigDict(env_prefix="FD_SCRIPTS_")

    datasets_dir: Path = Path("data/datasets")
    benchmarks_dir: Path = Path("data/benchmarks")

    clean_runs_per_task: int = Field(default=12, ge=1)
    doom_samples: int = Field(default=3, ge=1)
    dataset_concurrency: int = Field(default=6, ge=1)

    benchmark_concurrency: int = Field(default=3, ge=1)
    replay_concurrency: int = Field(default=12, ge=1)
