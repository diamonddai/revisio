from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    use_taxonomy: bool = Field(default=False, alias="USE_TAXONOMY")
    use_llm: bool = Field(default=False, alias="USE_LLM")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    sim_max_depth: int = Field(default=3, alias="SIM_MAX_DEPTH")


@lru_cache
def get_settings() -> Settings:
    return Settings()
