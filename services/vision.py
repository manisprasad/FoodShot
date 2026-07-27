import base64
import io

from loguru import logger
from openai import AsyncOpenAI
from PIL import Image
from pydantic import BaseModel

from core.config import config


class VisionAPIError(Exception):
    """Raised when the vision API fails to process the request."""

    pass


client = AsyncOpenAI(api_key=config.OPENAI_API_KEY, timeout=15.0)


class FoodRecognitionResult(BaseModel):
    dish_name: str
    dish_name_en: str
    weight_g: int
    confidence: str
    is_complex_meal: bool = False


def compress_image_for_vision(
    image_bytes: bytes, max_dim: int = 1024, quality: int = 85
) -> bytes:
    """Resize image preserving aspect ratio to max_dim and compress JPEG quality."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            width, height = img.size
            if max(width, height) > max_dim:
                if width > height:
                    new_width = max_dim
                    new_height = int(height * (max_dim / width))
                else:
                    new_height = max_dim
                    new_width = int(width * (max_dim / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            return output.getvalue()
    except Exception as e:
        logger.warning(f"Image compression failed, using original bytes: {e}")
        return image_bytes


async def analyze_food_photo(image_bytes: bytes, language: str = "en") -> dict | None:
    compressed_bytes = compress_image_for_vision(image_bytes)
    base64_image = base64.b64encode(compressed_bytes).decode("utf-8")

    prompt_text = (
        f"Identify the food in this image. "
        f"Reply with ONLY a JSON object with these fields: "
        f"dish_name (string, in {language} language), "
        f"dish_name_en (string, always in English), "
        f"weight_g (integer, estimated grams), "
        f"confidence (string: high, medium, or low), "
        f"is_complex_meal (boolean: true if plate contains 3+ separate unmixed components or ambiguous sides, false otherwise)."
    )

    async def _call_model(
        model_name: str, detail: str = "low"
    ) -> tuple[FoodRecognitionResult | None, int]:
        response = await client.beta.chat.completions.parse(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": detail,
                            },
                        },
                    ],
                }
            ],
            response_format=FoodRecognitionResult,
        )
        tokens = response.usage.total_tokens if response.usage else 0
        return response.choices[0].message.parsed, tokens

    try:
        # Tier 1: Fast & low-cost model (gpt-4o-mini with low detail ~85 image tokens)
        result, tokens_used = await _call_model(
            config.DEFAULT_VISION_MODEL, detail="low"
        )
        if not result:
            return None
        model_used = config.DEFAULT_VISION_MODEL

        # Tier 2 Escalation: If low confidence or complex multi-component meal, escalate to gpt-4o (high detail)
        if result.confidence == "low" or result.is_complex_meal:
            logger.info(
                f"Dynamic Cascade Triggered (confidence={result.confidence}, is_complex={result.is_complex_meal}). "
                f"Escalating from {config.DEFAULT_VISION_MODEL} to {config.ESCALATION_VISION_MODEL}..."
            )
            upgraded_result, upgraded_tokens = await _call_model(
                config.ESCALATION_VISION_MODEL, detail="auto"
            )
            if upgraded_result:
                result = upgraded_result
                model_used = config.ESCALATION_VISION_MODEL
                tokens_used += upgraded_tokens

        res_dict = result.model_dump()
        res_dict["model_used"] = model_used
        res_dict["total_tokens"] = tokens_used
        return res_dict

    except Exception as e:
        logger.error(f"Error during vision analysis: {e}")
        raise VisionAPIError("Vision API analysis failed") from e
