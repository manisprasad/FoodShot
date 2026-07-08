from unittest.mock import AsyncMock, patch
import pytest
from db import crud


@pytest.mark.asyncio
async def test_delete_user_success():
    session = AsyncMock()
    user = AsyncMock()

    with patch("db.crud.get_user", return_value=user) as mock_get_user:
        res = await crud.delete_user(session, 12345)

        assert res is True
        mock_get_user.assert_called_once_with(session, 12345)
        session.delete.assert_called_once_with(user)
        session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_delete_user_not_found():
    session = AsyncMock()

    with patch("db.crud.get_user", return_value=None) as mock_get_user:
        res = await crud.delete_user(session, 12345)

        assert res is False
        mock_get_user.assert_called_once_with(session, 12345)
        session.delete.assert_not_called()
        session.flush.assert_not_called()
