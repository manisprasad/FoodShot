import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.nutrition import USDAAPIError, get_nutrition_data


@pytest.mark.asyncio
async def test_get_nutrition_data_cache_hit():
    with patch("services.nutrition.redis_client", new_callable=AsyncMock) as mock_redis:
        mock_redis.get.return_value = json.dumps(
            {
                "carbs": 12.0,
                "protein": 0.3,
                "fat": 0.2,
                "kcal": 52.0,
            }
        )

        res = await get_nutrition_data("apple", 150)
        assert res == pytest.approx(
            {
                "carbs": 18.0,
                "protein": 0.45,
                "fat": 0.3,
                "kcal": 78.0,
            }
        )
        mock_redis.get.assert_called_once_with("nutrition:usda:apple")
        mock_redis.setex.assert_not_called()


@pytest.mark.asyncio
async def test_get_nutrition_data_cache_miss_success():
    with (
        patch("services.nutrition.redis_client", new_callable=AsyncMock) as mock_redis,
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):
        mock_redis.get.return_value = None

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "foods": [
                {
                    "foodNutrients": [
                        {
                            "nutrientName": "Carbohydrate, by difference",
                            "value": 10.0,
                            "unitName": "G",
                        },
                        {"nutrientName": "Protein", "value": 2.0, "unitName": "G"},
                        {
                            "nutrientName": "Total lipid (fat)",
                            "value": 1.5,
                            "unitName": "G",
                        },
                        {"nutrientName": "Energy", "value": 60.0, "unitName": "KCAL"},
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        res = await get_nutrition_data("testfood", 200)
        assert res == pytest.approx(
            {
                "carbs": 20.0,
                "protein": 4.0,
                "fat": 3.0,
                "kcal": 120.0,
            }
        )
        mock_redis.get.assert_called_once_with("nutrition:usda:testfood")
        mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_get_nutrition_data_usda_api_error():
    with (
        patch("services.nutrition.redis_client", new_callable=AsyncMock) as mock_redis,
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):
        mock_redis.get.return_value = None
        mock_get.side_effect = httpx.RequestError("Network connection failed")

        with pytest.raises(USDAAPIError, match="USDA API is temporarily unavailable"):
            await get_nutrition_data("apple", 150)


@pytest.mark.asyncio
async def test_get_nutrition_data_redis_read_failure():
    with (
        patch("services.nutrition.redis_client", new_callable=AsyncMock) as mock_redis,
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):
        mock_redis.get.side_effect = Exception("Redis connection error")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "foods": [
                {
                    "foodNutrients": [
                        {
                            "nutrientName": "Carbohydrate, by difference",
                            "value": 10.0,
                            "unitName": "G",
                        },
                        {"nutrientName": "Protein", "value": 2.0, "unitName": "G"},
                        {
                            "nutrientName": "Total lipid (fat)",
                            "value": 1.5,
                            "unitName": "G",
                        },
                        {"nutrientName": "Energy", "value": 60.0, "unitName": "KCAL"},
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        res = await get_nutrition_data("testfood", 100)
        assert res == pytest.approx(
            {
                "carbs": 10.0,
                "protein": 2.0,
                "fat": 1.5,
                "kcal": 60.0,
            }
        )
        mock_redis.get.assert_called_once_with("nutrition:usda:testfood")
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_nutrition_data_redis_write_failure():
    with (
        patch("services.nutrition.redis_client", new_callable=AsyncMock) as mock_redis,
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):
        mock_redis.get.return_value = None
        mock_redis.setex.side_effect = Exception("Redis write failed")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "foods": [
                {
                    "foodNutrients": [
                        {
                            "nutrientName": "Carbohydrate, by difference",
                            "value": 10.0,
                            "unitName": "G",
                        },
                        {"nutrientName": "Protein", "value": 2.0, "unitName": "G"},
                        {
                            "nutrientName": "Total lipid (fat)",
                            "value": 1.5,
                            "unitName": "G",
                        },
                        {"nutrientName": "Energy", "value": 60.0, "unitName": "KCAL"},
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        res = await get_nutrition_data("testfood", 100)
        assert res == pytest.approx(
            {
                "carbs": 10.0,
                "protein": 2.0,
                "fat": 1.5,
                "kcal": 60.0,
            }
        )
        mock_redis.get.assert_called_once_with("nutrition:usda:testfood")
        mock_redis.setex.assert_called_once()
