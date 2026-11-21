"""EngineSettings: samples per check, verify threshold, fallback window, model ids and timeouts."""

from typing import Self

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import SettingsConfigDict

from fd_shared.settings import SettingsBase


class EngineSettings(SettingsBase):
    """Every tunable number and model id the engine uses, read from `FD_ENGINE_*`."""

    model_config = SettingsConfigDict(env_prefix="FD_ENGINE_")

    strong_model: str = Field(min_length=1)
    openai_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("OPENAI_API_KEY")
    )

    samples_per_check: int = Field(default=3, ge=1)
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
