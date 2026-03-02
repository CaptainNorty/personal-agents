import json
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain.agents import create_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from loguru import logger
from sqlalchemy import select
from sqlalchemy.sql import func as sqlfunc

from app.bots.nutrition import nutritionix
from app.bots.nutrition.models import DailySummary, FoodItemCache, FoodLog
from app.common.llm import llm
from app.config import settings
from app.db.session import async_session

SYSTEM_PROMPT = """\
You are a personal nutrition tracking assistant on Telegram. Your job is to help \
the user track what they eat and provide macro breakdowns.

When the user tells you what they ate:
1. Use lookup_food to check for nutritional info
2. If not found in the database, use your own nutritional knowledge to estimate macros
3. Present a clear macro breakdown (calories, protein, fat, carbs, sugar) per item
4. Ask "Want me to log this?"
5. When they confirm (yes, yep, sure, go ahead, etc.), use log_food_items to save it
6. If they decline, acknowledge and move on

When the user asks about their daily intake (status, totals, "where am I at", etc.):
- Use get_todays_log and present the results

When you receive [SYSTEM:EOD_PROMPT]:
- Use get_todays_log to check what's been logged today
- Ask the user: "I'm about to write up your daily nutrition summary -- do you have \
anything else to add?"

When you receive [SYSTEM:EOD_TIMEOUT]:
- Use get_todays_log to get all items
- Generate a comprehensive daily summary with meal-by-meal breakdown, totals, and \
brief nutritional commentary
- Use save_daily_summary to store it
- Send the summary to the user

When the user responds to the end-of-day prompt:
- If they say they're done (no, done, that's it, etc.), generate and save the summary
- If they send more food, log it, then ask again if they have anything else

Keep responses concise and friendly. Format macros clearly.\
"""


def _get_local_now() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone))


def _get_meal_type(dt: datetime) -> str:
    hour = dt.hour
    if hour < 11:
        return "breakfast"
    elif hour < 15:
        return "lunch"
    elif hour < 21:
        return "dinner"
    else:
        return "snack"


@tool
async def lookup_food(query: str) -> str:
    """Look up nutritional info for a food item. Checks the local cache first,
    then queries the Nutritionix API. Returns macro breakdown or 'not found'."""
    normalized = query.strip().lower()

    # Check cache first
    async with async_session() as session:
        result = await session.execute(
            select(FoodItemCache).where(FoodItemCache.name_normalized == normalized)
        )
        cached = result.scalar_one_or_none()

    if cached:
        logger.info(f"Cache hit for '{query}'")
        return (
            f"Found in cache: {cached.name}\n"
            f"Serving: {cached.serving_qty} {cached.serving_unit}\n"
            f"Calories: {cached.calories} | Protein: {cached.protein_g}g | "
            f"Fat: {cached.fat_g}g | Carbs: {cached.carbs_g}g | Sugar: {cached.sugar_g}g\n"
            f"Source: {cached.source}"
        )

    # Query Nutritionix API
    foods = await nutritionix.lookup_food(query)
    if not foods:
        return f"Not found in database for '{query}'. Use your own nutritional knowledge to estimate."

    # Cache each result
    lines = []
    async with async_session() as session:
        for f in foods:
            name_norm = f["food_name"].strip().lower()
            # Check if already cached (could happen with multi-item queries)
            existing = await session.execute(
                select(FoodItemCache).where(FoodItemCache.name_normalized == name_norm)
            )
            if not existing.scalar_one_or_none():
                cache_entry = FoodItemCache(
                    name=f["food_name"],
                    name_normalized=name_norm,
                    protein_g=f["protein_g"],
                    fat_g=f["fat_g"],
                    carbs_g=f["carbs_g"],
                    sugar_g=f["sugar_g"],
                    calories=f["calories"],
                    serving_qty=f["serving_qty"],
                    serving_unit=f["serving_unit"],
                    source="nutritionix",
                )
                session.add(cache_entry)

            lines.append(
                f"{f['food_name']}\n"
                f"  Serving: {f['serving_qty']} {f['serving_unit']}\n"
                f"  Calories: {f['calories']} | Protein: {f['protein_g']}g | "
                f"  Fat: {f['fat_g']}g | Carbs: {f['carbs_g']}g | Sugar: {f['sugar_g']}g\n"
                f"  Source: nutritionix"
            )
        await session.commit()

    logger.info(f"Nutritionix lookup for '{query}': {len(foods)} item(s)")
    return "\n\n".join(lines)


@tool
async def log_food_items(items_json: str) -> str:
    """Log food items to the database. Takes a JSON array of items, each with:
    item_name, protein_g, fat_g, carbs_g, sugar_g, calories, serving_qty,
    serving_unit, source (either 'nutritionix' or 'claude_estimate')."""
    items = json.loads(items_json)
    now = _get_local_now()
    meal_type = _get_meal_type(now)

    async with async_session() as session:
        for item in items:
            log_entry = FoodLog(
                chat_id=settings.owner_chat_id,
                item_name=item["item_name"],
                protein_g=item["protein_g"],
                fat_g=item["fat_g"],
                carbs_g=item["carbs_g"],
                sugar_g=item["sugar_g"],
                calories=item["calories"],
                serving_qty=item.get("serving_qty", 1),
                serving_unit=item.get("serving_unit", "serving"),
                meal_type=meal_type,
                source=item.get("source", "nutritionix"),
                logged_at=now,
            )
            session.add(log_entry)

            # Also cache if not already cached
            name_norm = item["item_name"].strip().lower()
            existing = await session.execute(
                select(FoodItemCache).where(FoodItemCache.name_normalized == name_norm)
            )
            if not existing.scalar_one_or_none():
                cache_entry = FoodItemCache(
                    name=item["item_name"],
                    name_normalized=name_norm,
                    protein_g=item["protein_g"],
                    fat_g=item["fat_g"],
                    carbs_g=item["carbs_g"],
                    sugar_g=item["sugar_g"],
                    calories=item["calories"],
                    serving_qty=item.get("serving_qty", 1),
                    serving_unit=item.get("serving_unit", "serving"),
                    source=item.get("source", "nutritionix"),
                )
                session.add(cache_entry)

        await session.commit()

    logger.info(f"Logged {len(items)} food item(s) as {meal_type}")
    return f"Logged {len(items)} item(s) as {meal_type}."


@tool
async def get_todays_log() -> str:
    """Get all food items logged today, grouped by meal type with running totals."""
    today = _get_local_now().date()
    tz = ZoneInfo(settings.timezone)
    start = datetime.combine(today, datetime.min.time(), tzinfo=tz)
    end = datetime.combine(today, datetime.max.time(), tzinfo=tz)

    async with async_session() as session:
        result = await session.execute(
            select(FoodLog)
            .where(
                FoodLog.chat_id == settings.owner_chat_id,
                FoodLog.logged_at >= start,
                FoodLog.logged_at <= end,
            )
            .order_by(FoodLog.logged_at)
        )
        logs = result.scalars().all()

    if not logs:
        return "Nothing logged today yet."

    # Group by meal type
    meals: dict[str, list[FoodLog]] = {}
    for log in logs:
        meals.setdefault(log.meal_type, []).append(log)

    totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0, "sugar": 0.0}
    lines = []

    for meal_type in ["breakfast", "lunch", "dinner", "snack"]:
        if meal_type not in meals:
            continue
        lines.append(f"--- {meal_type.upper()} ---")
        for item in meals[meal_type]:
            lines.append(
                f"  {item.item_name} ({item.serving_qty} {item.serving_unit}): "
                f"{item.calories} cal | P:{item.protein_g}g F:{item.fat_g}g "
                f"C:{item.carbs_g}g S:{item.sugar_g}g"
            )
            totals["calories"] += item.calories
            totals["protein"] += item.protein_g
            totals["fat"] += item.fat_g
            totals["carbs"] += item.carbs_g
            totals["sugar"] += item.sugar_g

    lines.append("")
    lines.append("--- DAILY TOTALS ---")
    lines.append(
        f"Calories: {totals['calories']:.0f} | Protein: {totals['protein']:.1f}g | "
        f"Fat: {totals['fat']:.1f}g | Carbs: {totals['carbs']:.1f}g | "
        f"Sugar: {totals['sugar']:.1f}g"
    )

    return "\n".join(lines)


@tool
async def save_daily_summary(summary_text: str) -> str:
    """Save a daily nutrition summary. Computes totals from today's food log
    and stores the summary text along with aggregate macros."""
    today = _get_local_now().date()
    tz = ZoneInfo(settings.timezone)
    start = datetime.combine(today, datetime.min.time(), tzinfo=tz)
    end = datetime.combine(today, datetime.max.time(), tzinfo=tz)

    async with async_session() as session:
        # Compute totals
        result = await session.execute(
            select(
                sqlfunc.coalesce(sqlfunc.sum(FoodLog.protein_g), 0),
                sqlfunc.coalesce(sqlfunc.sum(FoodLog.fat_g), 0),
                sqlfunc.coalesce(sqlfunc.sum(FoodLog.carbs_g), 0),
                sqlfunc.coalesce(sqlfunc.sum(FoodLog.sugar_g), 0),
                sqlfunc.coalesce(sqlfunc.sum(FoodLog.calories), 0),
            ).where(
                FoodLog.chat_id == settings.owner_chat_id,
                FoodLog.logged_at >= start,
                FoodLog.logged_at <= end,
            )
        )
        row = result.one()
        protein, fat, carbs, sugar, calories = row

        # Check for existing summary
        existing = await session.execute(
            select(DailySummary).where(
                DailySummary.chat_id == settings.owner_chat_id,
                DailySummary.summary_date == today,
            )
        )
        if existing.scalar_one_or_none():
            return "Daily summary already exists for today."

        summary = DailySummary(
            chat_id=settings.owner_chat_id,
            summary_date=today,
            summary_text=summary_text,
            total_protein_g=protein,
            total_fat_g=fat,
            total_carbs_g=carbs,
            total_sugar_g=sugar,
            total_calories=calories,
        )
        session.add(summary)
        await session.commit()

    logger.info(f"Saved daily summary for {today}")
    return f"Daily summary saved for {today}."


checkpointer = InMemorySaver()

nutrition_agent = create_agent(
    model=llm,
    tools=[lookup_food, log_food_items, get_todays_log, save_daily_summary],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)
