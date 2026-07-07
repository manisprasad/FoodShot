from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.webhook import app
from core.config import config


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_webhook_success(client):
    with (
        patch("api.webhook.redis_client", new_callable=AsyncMock) as mock_redis,
        patch("api.webhook.dp.feed_update", new_callable=AsyncMock) as mock_feed,
    ):
        mock_redis.set.return_value = True

        headers = {"X-Telegram-Bot-Api-Secret-Token": config.WEBHOOK_SECRET_TOKEN}
        payload = {
            "update_id": 12345,
            "message": {
                "message_id": 1,
                "text": "/start",
                "chat": {"id": 999, "type": "private"},
                "date": 123456789,
            },
        }

        response = client.post("/webhook", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        mock_redis.set.assert_called_once_with(
            "processed_update:12345", "processing", ex=120, nx=True
        )
        mock_feed.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_invalid_secret_token(client):
    payload = {"update_id": 12345}
    headers = {"X-Telegram-Bot-Api-Secret-Token": "wrong_token"}
    response = client.post("/webhook", json=payload, headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_duplicate_update_id(client):
    with (
        patch("api.webhook.redis_client", new_callable=AsyncMock) as mock_redis,
        patch("api.webhook.dp.feed_update", new_callable=AsyncMock) as mock_feed,
    ):
        mock_redis.set.return_value = False

        headers = {"X-Telegram-Bot-Api-Secret-Token": config.WEBHOOK_SECRET_TOKEN}
        payload = {
            "update_id": 12345,
            "message": {
                "message_id": 1,
                "text": "hello",
                "chat": {"id": 999, "type": "private"},
                "date": 123456789,
            },
        }

        response = client.post("/webhook", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        mock_redis.set.assert_called_once_with(
            "processed_update:12345", "processing", ex=120, nx=True
        )
        mock_feed.assert_not_called()


@pytest.mark.asyncio
async def test_health_check_success(client):
    with (
        patch("api.webhook.SessionLocal") as mock_db,
        patch("api.webhook.redis_client", new_callable=AsyncMock) as mock_redis,
    ):
        # Configure async context manager mock for DB session
        mock_session = AsyncMock()
        mock_db.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session

        mock_redis.ping.return_value = True

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

        mock_session.execute.assert_called_once()
        mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_db_failure(client):
    with (
        patch("api.webhook.SessionLocal") as mock_db,
        patch("api.webhook.redis_client", new_callable=AsyncMock) as _mock_redis,
    ):
        mock_session = AsyncMock()
        mock_db.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session
        mock_session.execute.side_effect = Exception("DB Connection Refused")

        response = client.get("/health")
        assert response.status_code == 503
        assert "DB Connection Refused" in response.json()["detail"]


@pytest.mark.asyncio
async def test_health_check_redis_failure(client):
    with (
        patch("api.webhook.SessionLocal") as mock_db,
        patch("api.webhook.redis_client", new_callable=AsyncMock) as mock_redis,
    ):
        mock_session = AsyncMock()
        mock_db.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session

        mock_redis.ping.side_effect = Exception("Redis Connection Refused")

        response = client.get("/health")
        assert response.status_code == 503
        assert "Redis Connection Refused" in response.json()["detail"]
