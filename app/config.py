from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application configuration loaded from environment / .env file."""

    # App
    app_name: str = "Project Management Microservice"
    app_version: str = "1.0.0"
    debug: bool = True

    # Database — defaults to local SQLite so the service runs out of the box.
    # For PostgreSQL set: postgresql+asyncpg://user:pass@host:5432/dbname
    database_url: str = "sqlite+aiosqlite:///./project_management.db"
    sqlalchemy_echo: bool = False

    # Security / JWT
    secret_key: str = "change-me-in-production-please-use-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS — comma-separated list of allowed origins. "*" allows everything.
    cors_origins: str = "*"

    # URLs of sibling microservices (used by frontend / integration endpoints).
    # Empty string means "not configured yet" — the UI will show "em breve".
    ingestion_service_url: str = "https://mod2eng.azurewebsites.net/"
    reports_service_url: str = "https://moduloderelatorios.azurewebsites.net"
    presentations_service_url: str = "https://modulo4-apresentacoes-v2.azurewebsites.net/"
    diagrams_service_url: str = "https://modulo5-interface-e-nuvem.azurewebsites.net/"
    chat_service_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
