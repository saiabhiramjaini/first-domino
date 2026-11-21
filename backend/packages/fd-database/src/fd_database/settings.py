"""DatabaseSettings: connection URL and pool sizes."""

from pydantic import Field, SecretStr
from pydantic_settings import SettingsConfigDict

from fd_shared.settings import SettingsBase


class DatabaseSettings(SettingsBase):
    """Settings for the Postgres connection, read from `FD_DATABASE_*` variables."""

    model_config = SettingsConfigDict(env_prefix="FD_DATABASE_")

    url: SecretStr = SecretStr("postgresql+asyncpg://fd:fd@localhost:5432/first_domino")
    pool_size: int = Field(default=10, ge=1)
    max_overflow: int = Field(default=10, ge=0)
    pool_timeout_seconds: float = Field(default=10.0, gt=0)
    echo: bool = False
