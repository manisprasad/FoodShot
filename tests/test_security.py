from unittest.mock import AsyncMock, MagicMock

import pytest

from services.security import check_photo_security_limits


@pytest.mark.asyncio
async def test_admin_bypasses_security_limits():
    mock_redis = AsyncMock()
    result = await check_photo_security_limits(mock_redis, user_id=123, is_admin=True)
    assert result.allowed is True
    mock_redis.ttl.assert_not_called()


@pytest.mark.asyncio
async def test_user_under_cooldown_blocked():
    mock_redis = AsyncMock()
    mock_redis.ttl.return_value = 180  # 3 minutes remaining

    result = await check_photo_security_limits(mock_redis, user_id=123, is_admin=False)
    assert result.allowed is False
    assert result.reason == "burst_cooldown"
    assert result.retry_after == 180


@pytest.mark.asyncio
async def test_user_triggers_burst_cooldown():
    mock_redis = AsyncMock()
    mock_redis.ttl.return_value = -2  # key does not exist

    pipe_mock = AsyncMock()
    pipe_mock.execute.return_value = [4]  # 4th request in 30s
    mock_redis.pipeline = MagicMock(return_value=pipe_mock)

    result = await check_photo_security_limits(mock_redis, user_id=123, is_admin=False)
    assert result.allowed is False
    assert result.reason == "burst_limit"
    assert result.retry_after == 300
    mock_redis.setex.assert_called_once_with("security:cooldown:123", 300, "1")
