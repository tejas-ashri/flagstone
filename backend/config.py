from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+asyncpg://flagstone:flagstone@localhost:5432/flagstone_dev"
    sdk_key: str = "sdk-dev-key"
    poll_interval_seconds: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
