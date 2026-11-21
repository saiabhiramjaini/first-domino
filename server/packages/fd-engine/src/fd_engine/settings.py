"""EngineSettings: samples per check, verify threshold, fallback window, model ids and timeouts."""

from typing import Self

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import SettingsConfigDict

from fd_shared.settings import SettingsBase


class EngineSettings(SettingsBase):
    """Every tunable number and model id the engine uses, read from `FD_ENGINE_*`."""

    model_config = SettingsConfigDict(env_prefix="FD_ENGINE_", env_parse_none_str="null")

    strong_model: str = Field(min_length=1)
    openai_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("OPENAI_API_KEY")
    )
    judge_model: str | None = Field(default=None, min_length=1)
    """The model that judges each replay of a flagged run against its failure reason.

    None uses `strong_model`. A flagged run has no code check that sees its failure, so this
    model decides every replay's outcome in its diagnosis.
    """
    judge_temperature: float | None = Field(default=None, ge=0, le=2)
    """Sampling temperature of the judge. None sends none, so the model uses its default.

    None by default because reasoning models reject any temperature but their default, which
    would fail every judge call. Set 0 for a model that accepts it, so the same replay gets
    the same verdict; the search already tolerates some judge noise through its rechecks.
    """

    bisect_with_strong_model: bool = False
    """Bisect replays on `strong_model` instead of the agent's own model.

    Off by default: a stronger model recovers from mistakes the agent itself never recovers
    from, so bisect lands late. Measured on planted-bug calls.
    """
    calibrate: bool = True
    """Before the search, check that a replay keeping every recorded step fails.

    The search assumes the failed run is doomed with all its steps kept. A check that passes
    such a replay is flaky or does not judge this run, so any step it blamed would be wrong.
    Keeping every step answers each recorded model call from the recording, so the check is
    nearly free.
    """
    calibration_samples: int = Field(default=2, ge=1)
    """Replays in the calibration check. One pass stops the diagnosis as `check_inconsistent`.

    Cheap for the reason above, so a second replay buys a second chance to catch a flaky check.
    """
    samples_per_check: int = Field(default=3, ge=1)
    doomed_recheck_samples: int = Field(default=3, ge=0)
    """Extra replays for a save point whose first check had no pass, before calling it doomed.

    One check of 3 replays wrongly looks doomed 1 time in 8 when a save point passes half the
    time, which blames a step too early. A second round brings that to 1 in 64. Only doomed
    checks pay for it: one pass already shows a save point can succeed.
    """
    verify_samples: int = Field(default=5, ge=1)
    verify_pass_threshold: int = Field(default=3, ge=1)
    fallback_window: int = Field(default=2, ge=0)
    max_checks: int = Field(default=24, ge=2)
    replay_timeout_seconds: float = Field(default=900.0, gt=0)

    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_parse_retries: int = Field(default=1, ge=0)
    llm_input_usd_per_million_tokens: float = Field(default=2.5, ge=0)
    llm_output_usd_per_million_tokens: float = Field(default=10.0, ge=0)

    @model_validator(mode="after")
    def _threshold_fits_samples(self) -> Self:
        if self.verify_pass_threshold > self.verify_samples:
            msg = "verify_pass_threshold must not exceed verify_samples"
            raise ValueError(msg)
        return self
