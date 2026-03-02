import httpx
from loguru import logger

from app.config import settings

NUTRITIONIX_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"


async def lookup_food(query: str) -> list[dict] | None:
    """Look up nutritional info via Nutritionix natural language endpoint.

    Returns a list of food item dicts on success, or None on failure.
    """
    if not settings.nutritionix_app_id or not settings.nutritionix_api_key:
        logger.warning("Nutritionix API credentials not configured")
        return None

    headers = {
        "x-app-id": settings.nutritionix_app_id,
        "x-app-key": settings.nutritionix_api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                NUTRITIONIX_URL,
                headers=headers,
                json={"query": query},
                timeout=10.0,
            )
            if not resp.is_success:
                logger.warning(f"Nutritionix API error {resp.status_code}: {resp.text}")
                return None

            data = resp.json()
            foods = data.get("foods", [])
            return [
                {
                    "food_name": f["food_name"],
                    "protein_g": f.get("nf_protein", 0),
                    "fat_g": f.get("nf_total_fat", 0),
                    "carbs_g": f.get("nf_total_carbohydrate", 0),
                    "sugar_g": f.get("nf_sugars", 0),
                    "calories": f.get("nf_calories", 0),
                    "serving_qty": f.get("serving_qty", 1),
                    "serving_unit": f.get("serving_unit", "serving"),
                }
                for f in foods
            ]
        except httpx.HTTPError as e:
            logger.error(f"Nutritionix request failed: {e}")
            return None
