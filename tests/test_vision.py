from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.vision import VisionAPIError, analyze_food_photo


@pytest.mark.asyncio
async def test_analyze_food_photo_success():
    with patch(
        "services.vision.client.beta.chat.completions.parse", new_callable=AsyncMock
    ) as mock_parse:
        mock_parsed = MagicMock()
        mock_parsed.model_dump.return_value = {
            "dish_name": "яблуко",
            "dish_name_en": "apple",
            "weight_g": 150,
            "confidence": "high",
        }

        mock_choice = AsyncMock()
        mock_choice.message.parsed = mock_parsed

        mock_response = AsyncMock()
        mock_response.choices = [mock_choice]
        mock_parse.return_value = mock_response

        res = await analyze_food_photo(b"dummy_bytes", language="uk")
        assert res == {
            "dish_name": "яблуко",
            "dish_name_en": "apple",
            "weight_g": 150,
            "confidence": "high",
        }
        mock_parse.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_food_photo_api_error():
    with patch(
        "services.vision.client.beta.chat.completions.parse", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.side_effect = Exception("API connection error")

        with pytest.raises(VisionAPIError, match="Vision API analysis failed"):
            await analyze_food_photo(b"dummy_bytes", language="en")
