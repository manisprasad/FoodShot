import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from services.vision import (
    VisionAPIError,
    analyze_food_photo,
    compress_image_for_vision,
)


def test_compress_image_for_vision_resizes_large_image():
    # Create large 2000x1500 RGB image
    img = Image.new("RGB", (2000, 1500), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    raw_bytes = buf.getvalue()

    compressed_bytes = compress_image_for_vision(raw_bytes, max_dim=1024, quality=85)
    assert len(compressed_bytes) < len(raw_bytes)

    with Image.open(io.BytesIO(compressed_bytes)) as result_img:
        assert max(result_img.size) == 1024


@pytest.mark.asyncio
async def test_analyze_food_photo_success_single_call():
    with patch(
        "services.vision.client.beta.chat.completions.parse", new_callable=AsyncMock
    ) as mock_parse:
        mock_parsed = MagicMock()
        mock_parsed.confidence = "high"
        mock_parsed.is_complex_meal = False
        mock_parsed.model_dump.return_value = {
            "dish_name": "яблуко",
            "dish_name_en": "apple",
            "weight_g": 150,
            "confidence": "high",
            "is_complex_meal": False,
        }

        mock_choice = AsyncMock()
        mock_choice.message.parsed = mock_parsed

        mock_response = AsyncMock()
        mock_response.choices = [mock_choice]
        mock_parse.return_value = mock_response

        res = await analyze_food_photo(b"dummy_bytes", language="uk")
        assert res["dish_name"] == "яблуко"
        assert res["confidence"] == "high"
        assert mock_parse.call_count == 1


@pytest.mark.asyncio
async def test_analyze_food_photo_escalates_on_complex_meal():
    with patch(
        "services.vision.client.beta.chat.completions.parse", new_callable=AsyncMock
    ) as mock_parse:
        # First call (gpt-4o-mini): returns complex meal
        mock_mini_parsed = MagicMock()
        mock_mini_parsed.confidence = "medium"
        mock_mini_parsed.is_complex_meal = True

        # Second call (gpt-4o): returns upgraded response
        mock_4o_parsed = MagicMock()
        mock_4o_parsed.confidence = "high"
        mock_4o_parsed.is_complex_meal = True
        mock_4o_parsed.model_dump.return_value = {
            "dish_name": "Стейк з гарніром",
            "dish_name_en": "Steak with side salad and potatoes",
            "weight_g": 450,
            "confidence": "high",
            "is_complex_meal": True,
        }

        mock_response_1 = AsyncMock()
        mock_response_1.choices = [
            MagicMock(message=MagicMock(parsed=mock_mini_parsed))
        ]

        mock_response_2 = AsyncMock()
        mock_response_2.choices = [MagicMock(message=MagicMock(parsed=mock_4o_parsed))]

        mock_parse.side_effect = [mock_response_1, mock_response_2]

        res = await analyze_food_photo(b"dummy_bytes", language="uk")
        assert res["dish_name_en"] == "Steak with side salad and potatoes"
        assert mock_parse.call_count == 2


@pytest.mark.asyncio
async def test_analyze_food_photo_api_error():
    with patch(
        "services.vision.client.beta.chat.completions.parse", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.side_effect = Exception("API connection error")

        with pytest.raises(VisionAPIError, match="Vision API analysis failed"):
            await analyze_food_photo(b"dummy_bytes", language="en")
