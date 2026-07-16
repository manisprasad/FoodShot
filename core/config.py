from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str | None = None
    USDA_API_KEY: str | None = None
    NUTRITIONIX_APP_ID: str | None = None
    NUTRITIONIX_API_KEY: str | None = None
    DATABASE_URL: str
    REDIS_URL: str
    WEBHOOK_URL: str
    WEBHOOK_SECRET_TOKEN: str
    CLOUDFLARE_TUNNEL_TOKEN: str | None = None
    ADMIN_ID: int | None = None
    PORT: int = 8000

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def rewrite_postgres_scheme(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith(
                "postgresql+asyncpg://"
            ):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

            # Strip sslmode because asyncpg doesn't accept it
            try:
                parsed = urlparse(v)
                if parsed.query:
                    query_params = dict(parse_qsl(parsed.query))
                    if "sslmode" in query_params:
                        del query_params["sslmode"]
                        new_query = urlencode(query_params)
                        parsed = parsed._replace(query=new_query)
                        v = urlunparse(parsed)
            except Exception:
                pass
        return v

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


config = Settings()
