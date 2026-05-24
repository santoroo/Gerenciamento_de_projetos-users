from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings"""

    # App
    app_name: str = "Project Management Microservice"
    app_version: str = "1.0.0"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/project_management_db"
    sqlalchemy_echo: bool = False

    # JWT/Security
    secret_key: str = "your_super_secret_key_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
