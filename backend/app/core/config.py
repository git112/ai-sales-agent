from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(str(ROOT / ".env"), ".env"), extra="ignore")

    app_env: str = "hackathon"
    jwt_secret: str = "lumina-hackathon-local-dev-secret-change-me"
    jwt_expire_minutes: int = 720
    cors_origins: str = "http://localhost:5173"
    default_app_mode: str = "demo"
    upload_dir: str = "uploads"
    chroma_path: str = "chroma"
    ai_provider: str = "demo"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"


settings = Settings()
