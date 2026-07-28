from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from db.models import User
from services.freemium import check_daily_freemium_quota, grant_user_premium


@pytest.mark.asyncio
async def test_admin_gets_unlimited_freemium_quota():
    mock_redis = AsyncMock()
    user = User(id=1, is_premium=False)

    result = await check_daily_freemium_quota(user=user, is_admin=True, redis=mock_redis)
    assert result.allowed is True
    assert result.is_premium is True
    mock_redis.pipeline.assert_not_called()


@pytest.mark.asyncio
async def test_premium_user_within_15_daily_limit():
    mock_redis = AsyncMock()
    pipe_mock = MagicMock()
    pipe_mock.execute = AsyncMock(return_value=[12])  # 12th photo today
    mock_redis.pipeline = MagicMock(return_value=pipe_mock)

    now_utc = datetime.now(UTC).replace(tzinfo=None)
    user = User(
        id=2,
        is_premium=True,
        premium_until=now_utc + timedelta(days=10),
    )

    result = await check_daily_freemium_quota(
        user=user, is_admin=False, redis=mock_redis
    )
    assert result.allowed is True
    assert result.is_premium is True
    assert result.daily_limit == 15
    assert result.used_today == 12


@pytest.mark.asyncio
async def test_premium_user_exceeds_15_daily_limit():
    mock_redis = AsyncMock()
    pipe_mock = MagicMock()
    pipe_mock.execute = AsyncMock(return_value=[16])  # 16th photo today (limit 15)
    mock_redis.pipeline = MagicMock(return_value=pipe_mock)

    now_utc = datetime.now(UTC).replace(tzinfo=None)
    user = User(
        id=2,
        is_premium=True,
        premium_until=now_utc + timedelta(days=10),
    )

    result = await check_daily_freemium_quota(
        user=user, is_admin=False, redis=mock_redis
    )
    assert result.allowed is False
    assert result.is_premium is True
    assert result.daily_limit == 15
    assert result.used_today == 16


@pytest.mark.asyncio
async def test_free_user_within_daily_limit():
    mock_redis = AsyncMock()
    pipe_mock = MagicMock()
    pipe_mock.execute = AsyncMock(return_value=[3])  # 3rd photo today
    mock_redis.pipeline = MagicMock(return_value=pipe_mock)

    user = User(id=3, is_premium=False)
    result = await check_daily_freemium_quota(user=user, is_admin=False, redis=mock_redis)
    assert result.allowed is True
    assert result.used_today == 3


@pytest.mark.asyncio
async def test_free_user_exceeds_daily_limit():
    mock_redis = AsyncMock()
    pipe_mock = MagicMock()
    pipe_mock.execute = AsyncMock(return_value=[6])  # 6th photo today (limit is 5)
    mock_redis.pipeline = MagicMock(return_value=pipe_mock)

    user = User(id=4, is_premium=False)
    result = await check_daily_freemium_quota(user=user, is_admin=False, redis=mock_redis)
    assert result.allowed is False
    assert result.used_today == 6


@pytest.mark.asyncio
async def test_grant_user_premium_success():
    mock_session = AsyncMock()
    mock_user = User(id=5, is_premium=False, premium_until=None)

    with pytest.MonkeyPatch.context() as m:
        m.setattr("db.crud.get_user", AsyncMock(return_value=mock_user))
        updated_user = await grant_user_premium(mock_session, user_id=5, days=30)
        assert updated_user.is_premium is True
        assert updated_user.premium_until is not None
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_grant_user_premium_minutes():
    mock_session = AsyncMock()
    mock_user = User(id=6, is_premium=False, premium_until=None)

    with pytest.MonkeyPatch.context() as m:
        m.setattr("db.crud.get_user", AsyncMock(return_value=mock_user))
        updated_user = await grant_user_premium(mock_session, user_id=6, minutes=10)
        assert updated_user.is_premium is True
        assert updated_user.premium_until is not None
        mock_session.commit.assert_called_once()
