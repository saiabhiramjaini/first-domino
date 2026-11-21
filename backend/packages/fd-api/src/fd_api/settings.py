"""ApiSettings: Clerk issuer, allowed origins, job lease time and the OpenAPI export path."""

from pathlib import Path

from pydantic import Field
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
    clerk_issuer: str | None = None
    clerk_jwks_url: str | None = None
    openapi_path: Path = Field(
        default=Path("../api/openapi.json"),
        description="Where `make openapi` writes the schema, relative to `backend/`.",
    )
