"""ApiSettings: web token secret, allowed origins, job lease time and list limits."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import SettingsConfigDict

from fd_shared.settings import SettingsBase


class ApiSettings(SettingsBase):
    """Settings for the control plane API, read from `FD_API_*` variables."""

    model_config = SettingsConfigDict(env_prefix="FD_API_")

    cors_origins: list[str] = Field(default=["http://localhost:3000"])
    log_level: str = "INFO"
    log_json: bool = False
    lease_seconds: int = Field(default=120, ge=1)
    max_job_attempts: int = Field(default=3, ge=1)
    lease_poll_interval_seconds: float = Field(default=0.5, gt=0)
    replay_poll_interval_seconds: float = Field(default=1.0, gt=0)
    slack_timeout_seconds: float = Field(default=5.0, gt=0)
    web_jwt_secret: SecretStr = Field(
        default=SecretStr(""),
        description="HS256 secret shared with the web app for its session tokens.",
    )
    openapi_path: Path = Field(
        default=Path("../api/openapi.json"),
        description="Where `make openapi` writes the schema, relative to `backend/`.",
    )
