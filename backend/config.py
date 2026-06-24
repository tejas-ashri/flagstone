from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://flagstone:flagstone@localhost:5432/flagstone_dev"
    sdk_key: str = "sdk-dev-key"

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()
