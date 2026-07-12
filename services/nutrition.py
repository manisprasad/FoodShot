import json

import httpx
from loguru import logger

from core.config import config
from core.redis_client import redis_client


class USDAAPIError(Exception):
    """Raised when the USDA API fails to process the request."""

    pass


async def get_nutrition_data(query: str, weight_g: int) -> dict:
    cache_key = f"nutrition:usda:{query.lower()}"
    cached_data = None
    try:
        cached_data = await redis_client.get(cache_key)
    except Exception as e:
        logger.warning(f"Redis get failed: {e}. Falling back to USDA API.")

    if cached_data:
        logger.info(f"Nutrition cache HIT for: {query}")
        base_nutrients = json.loads(cached_data)
    else:
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        params = {"api_key": config.USDA_API_KEY, "query": query, "pageSize": 1}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.info(
                    f"Nutrition cache MISS. Fetching from USDA API for: {query}"
                )
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(f"USDA API request failed for query {query}: {e}")
            raise USDAAPIError("USDA API is temporarily unavailable") from e

        if not data.get("foods"):
            return None

        food = data["foods"][0]
        nutrients = {}
        for n in food.get("foodNutrients", []):
            name = n["nutrientName"]
            if name == "Energy" and n.get("unitName", "").upper() != "KCAL":
                continue
            nutrients[name] = n["value"]

        base_nutrients = {
            "carbs": nutrients.get("Carbohydrate, by difference", 0),
            "protein": nutrients.get("Protein", 0),
            "fat": nutrients.get("Total lipid (fat)", 0),
            "kcal": nutrients.get("Energy", 0),
        }

        try:
            await redis_client.setex(cache_key, 604800, json.dumps(base_nutrients))
        except Exception as e:
            logger.warning(f"Redis setex failed: {e}")

    ratio = weight_g / 100

    return {
        "carbs": base_nutrients["carbs"] * ratio,
        "protein": base_nutrients["protein"] * ratio,
        "fat": base_nutrients["fat"] * ratio,
        "kcal": base_nutrients["kcal"] * ratio,
    }
