from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings. Load from env vars or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    db_url: str = "sqlite:///exam.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    # Secrets (set via env vars, never commit .env)
    secret_key: str | None = None


settings = Settings()
