from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bots.nutrition.models import NutritionEntry
from app.common.telegram import send_message
from app.config import settings


async def handle_message(chat_id: str, text: str, session: AsyncSession) -> None:
    """Handle an incoming reply to a nutrition prompt."""
    token = settings.telegram_nutrition_bot_token

    # Find the most recent unanswered prompt
    result = await session.execute(
        select(NutritionEntry)
        .where(NutritionEntry.response_text.is_(None))
        .order_by(NutritionEntry.prompt_sent_at.desc())
        .limit(1)
    )
    entry = result.scalar_one_or_none()

    if entry:
        entry.response_text = text
        entry.responded_at = datetime.now(timezone.utc)
        await session.commit()
        await send_message(token, chat_id, "Got it, logged!")
        logger.info("Nutrition response logged")
    else:
        await send_message(token, chat_id, "No pending nutrition prompt to respond to.")
