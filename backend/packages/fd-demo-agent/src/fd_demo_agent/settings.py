"""DemoAgentSettings: agent model, step limit and the OpenAI key."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DemoAgentSettings(BaseSettings):
    """Settings for the demo customer, read from `FD_DEMO_AGENT_*` and `backend/.env`.

    The fixed current time is part of the world data (`world/data/user.json`), because the
    calendar and the calls are anchored to it.
    """

    model_config = SettingsConfigDict(
        env_prefix="FD_DEMO_AGENT_", env_file=".env", extra="ignore", populate_by_name=True
    )

    model: str = Field(min_length=1, description="Model id the agent runs with.")
    max_steps: int = Field(default=20, ge=1, description="A run stops after this many steps.")
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
