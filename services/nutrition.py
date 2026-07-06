import httpx

import json

from core.config import config
from core.redis_client import redis_client
from loguru import logger


async def get_nutrition_data(query: str, weight_g: int) -> dict:
    cache_key = f"nutrition:usda:{query.lower()}"
    cached_data = await redis_client.get(cache_key)

    if cached_data:
        logger.info(f"Nutrition cache HIT for: {query}")
        base_nutrients = json.loads(cached_data)
    else:
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        params = {"api_key": config.USDA_API_KEY, "query": query, "pageSize": 1}

        async with httpx.AsyncClient() as client:
            logger.info(f"Nutrition cache MISS. Fetching from USDA API for: {query}")
            response = await client.get(url, params=params)
            data = response.json()

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

        await redis_client.setex(cache_key, 604800, json.dumps(base_nutrients))

    ratio = weight_g / 100

    return {
        "carbs": base_nutrients["carbs"] * ratio,
        "protein": base_nutrients["protein"] * ratio,
        "fat": base_nutrients["fat"] * ratio,
        "kcal": base_nutrients["kcal"] * ratio,
    }
