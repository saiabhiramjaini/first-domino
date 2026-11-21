"""Settings base class that every package's settings class extends."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsBase(BaseSettings):
    """Reads the environment and `.env`, ignoring keys that belong to other packages.

    Subclasses set their own `env_prefix` and are built by injection, never at module scope.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)
