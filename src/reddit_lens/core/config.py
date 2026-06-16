from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application configuration, loaded from environment
    variables or a .env file. Using pydantic-settings gives us type
    validation and a single source of truth instead of scattered
    os.environ.get() calls across the codebase.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Hacker News API (public, no authentication required)
    hn_base_url: str = "https://hacker-news.firebaseio.com"

    # Database (used starting Phase 1.3)
    database_url: str = ""

    # Redis (used starting Phase 2)
    redis_url: str = ""

    # App
    environment: str = "development"
    log_level: str = "INFO"

    @property
    def sync_database_url(self) -> str:
        """
        Alembic runs migrations synchronously, so it needs the
        psycopg2 driver instead of the asyncpg one used by the app
        at runtime. We derive it from the same DATABASE_URL so
        there's only one source of truth for connection details.
        """
        return self.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")


settings = Settings()