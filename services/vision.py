import base64

from openai import AsyncOpenAI
from pydantic import BaseModel

from core.config import config

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


class FoodRecognitionResult(BaseModel):
    dish_name: str
    dish_name_en: str
    weight_g: int
    confidence: str


async def analyze_food_photo(image_bytes: bytes, language: str = "en") -> dict | None:
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    try:
        response = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Identify the food in this image. "
                                f"Reply with ONLY a JSON object with these fields: "
                                f"dish_name (string, in {language} language), "
                                f"dish_name_en (string, always in English), "
                                f"weight_g (integer, estimated grams), "
                                f"confidence (string: high, medium, or low)."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            response_format=FoodRecognitionResult,
        )

        parsed_result = response.choices[0].message.parsed
        if not parsed_result:
            return None

        return parsed_result.model_dump()

    except Exception as e:
        print(f"Error during vision analysis: {e}")
        return None
