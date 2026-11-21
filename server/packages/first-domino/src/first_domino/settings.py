"""SdkSettings: API key, base URL and worker tunables, read with the FIRST_DOMINO_ prefix."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SdkSettings(BaseSettings):
    """SDK settings, read from `FIRST_DOMINO_*` environment variables and `.env`.

    Example:
        >>> SdkSettings(api_key="fd_live_...", base_url="https://api.example.com")
    """

    model_config = SettingsConfigDict(env_prefix="FIRST_DOMINO_", env_file=".env", extra="ignore")

    api_key: SecretStr | None = Field(
        default=None, description="Project API key. Without it, recording is a no-op."
    )
    base_url: str = Field(
        default="https://api-first-domino.abhiramtech.in", description="First Domino API URL."
    )
    timeout_seconds: float = Field(default=30.0, gt=0, description="Timeout of one API call.")
    lease_wait_seconds: int = Field(
        default=10, ge=0, le=20, description="How long one lease call waits for a job."
    )
    worker_concurrency: int = Field(
        default=4, ge=1, description="Replay jobs one worker runs at the same time."
    )
    diagnosis_poll_seconds: float = Field(
        default=1.0, gt=0, description="Pause between polls while waiting for a diagnosis."
    )
    worker_retry_seconds: float = Field(
        default=2.0, ge=0, description="Pause before leasing again after the API failed."
    )
