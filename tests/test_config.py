from core.config import Settings


def test_database_url_validation_rewrites_scheme_and_strips_sslmode():
    # 1. postgres:// with sslmode
    settings = Settings.model_validate(
        {
            "BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_key",
            "DATABASE_URL": "postgres://user:pass@host:5432/db?sslmode=disable&param=value",
            "REDIS_URL": "redis://localhost:6379/0",
            "WEBHOOK_URL": "https://example.com/webhook",
            "WEBHOOK_SECRET_TOKEN": "secret",
        }
    )
    assert (
        settings.DATABASE_URL
        == "postgresql+asyncpg://user:pass@host:5432/db?param=value"
    )

    # 2. postgresql:// with sslmode
    settings = Settings.model_validate(
        {
            "BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_key",
            "DATABASE_URL": "postgresql://user:pass@host:5432/db?sslmode=require",
            "REDIS_URL": "redis://localhost:6379/0",
            "WEBHOOK_URL": "https://example.com/webhook",
            "WEBHOOK_SECRET_TOKEN": "secret",
        }
    )
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@host:5432/db"

    # 3. Already correct url
    settings = Settings.model_validate(
        {
            "BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_key",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@host:5432/db",
            "REDIS_URL": "redis://localhost:6379/0",
            "WEBHOOK_URL": "https://example.com/webhook",
            "WEBHOOK_SECRET_TOKEN": "secret",
        }
    )
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@host:5432/db"


def test_timezone_offset_hours_default_and_custom():
    settings_default = Settings.model_validate(
        {
            "BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_key",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@host:5432/db",
            "REDIS_URL": "redis://localhost:6379/0",
            "WEBHOOK_URL": "https://example.com/webhook",
            "WEBHOOK_SECRET_TOKEN": "secret",
        }
    )
    assert settings_default.TIMEZONE_OFFSET_HOURS == 3

    settings_custom = Settings.model_validate(
        {
            "BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_key",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@host:5432/db",
            "REDIS_URL": "redis://localhost:6379/0",
            "WEBHOOK_URL": "https://example.com/webhook",
            "WEBHOOK_SECRET_TOKEN": "secret",
            "TIMEZONE_OFFSET_HOURS": "5",
        }
    )
    assert settings_custom.TIMEZONE_OFFSET_HOURS == 5
