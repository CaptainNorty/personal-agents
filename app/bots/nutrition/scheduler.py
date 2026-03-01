from datetime import datetime, timezone

from loguru import logger

from app.bots.nutrition.models import NutritionEntry
from app.common.scheduler import register_job
from app.common.telegram import send_message
from app.config import settings
from app.db.session import async_session


async def send_nutrition_prompt() -> None:
    """Scheduled job: send daily nutrition prompt."""
    async with async_session() as session:
        entry = NutritionEntry(prompt_sent_at=datetime.now(timezone.utc))
        session.add(entry)
        await session.commit()

    await send_message(
        settings.telegram_nutrition_bot_token,
        settings.owner_chat_id,
        "What did you eat today?",
    )
    logger.info("Sent nutrition prompt")


def register_nutrition_jobs() -> None:
    """Register daily nutrition prompt at 6pm."""
    register_job(
        send_nutrition_prompt,
        "cron",
        hour=18,
        minute=0,
        id="nutrition_daily_prompt",
        replace_existing=True,
    )
