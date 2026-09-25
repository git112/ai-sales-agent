from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]

# Push root .env into os.environ so modules that use os.getenv (Calendly,
# Twilio, etc.) see the same values as pydantic Settings — without requiring
# a shell export or a manual restart dance after editing .env.
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(str(ROOT / ".env"), ".env"), extra="ignore")

    app_env: str = "hackathon"
    jwt_secret: str = "lumina-hackathon-local-dev-secret-change-me"
    jwt_expire_minutes: int = 720
    cors_origins: str = "http://localhost:5173"
    default_app_mode: str = "demo"
    upload_dir: str = "uploads"
    chroma_path: str = "chroma"
    sqlite_path: str = "data/sales_agent.db"
    ai_provider: str = "demo"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ai_base_url: str | None = None
    ai_timeout_seconds: float = 10
    ai_max_output_tokens: int = 800
    url_cache_ttl_seconds: int = 21600

    bolna_api_key: str | None = None
    bolna_base_url: str = "https://api.bolna.ai"
    bolna_from_phone: str | None = None
    bolna_default_agent_type: str = "other"
    bolna_webhook_url: str | None = None


settings = Settings()
