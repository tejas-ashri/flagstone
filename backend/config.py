from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+asyncpg://flagstone:flagstone@localhost:5432/flagstone_dev"
    # Seeded at startup as an SDK key of the Default project, so existing SDK
    # clients keep working. Further keys are created per project in the UI.
    sdk_key: str = "sdk-dev-key"
    poll_interval_seconds: int = 30

    # URL the browser uses to reach the admin UI. OAuth redirect URIs are
    # built from it: {public_url}/auth/{provider}/callback
    public_url: str = "http://localhost:5173"
    # Set to true whenever the UI is served over HTTPS.
    cookie_secure: bool = False
    session_ttl_hours: int = 24 * 7

    github_client_id: str = ""
    github_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    slack_client_id: str = ""
    slack_client_secret: str = ""

    # Comma-separated emails that are made admins of the Default project when
    # they sign in. This is how the first admin gets access.
    admin_emails: str = ""

    # Passwordless sign-in by email, for local development only. Never enable
    # this on a deployment reachable by others.
    dev_login: bool = False

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
