from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: Optional[str] = None
    USDA_API_KEY: Optional[str] = None
    NUTRITIONIX_APP_ID: Optional[str] = None
    NUTRITIONIX_API_KEY: Optional[str] = None
    DATABASE_URL: str
    REDIS_URL: str
    WEBHOOK_URL: str
    WEBHOOK_SECRET_TOKEN: str
    CLOUDFLARE_TUNNEL_TOKEN: Optional[str] = None
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


config = Settings()
