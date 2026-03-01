from datetime import datetime, timezone

from loguru import logger

from app.bots.social.models import SocialEntry
from app.common.scheduler import register_job
from app.common.telegram import send_message
from app.config import settings
from app.db.session import async_session

SOCIAL_PROMPT = (
    "What are your social plans for this week? Reminder that your social muscles "
    "can be exercised just like your software engineering knowledge \u2014 how are you "
    "going to exercise those muscles this week?"
)


async def send_social_prompt() -> None:
    """Scheduled job: send weekly social accountability prompt."""
    async with async_session() as session:
        entry = SocialEntry(prompt_sent_at=datetime.now(timezone.utc))
        session.add(entry)
        await session.commit()

    await send_message(
        settings.telegram_social_bot_token,
        settings.owner_chat_id,
        SOCIAL_PROMPT,
    )
    logger.info("Sent social prompt")


def register_social_jobs() -> None:
    """Register weekly social prompt for Sunday at 9am."""
    register_job(
        send_social_prompt,
        "cron",
        day_of_week="sun",
        hour=9,
        minute=0,
        id="social_weekly_prompt",
        replace_existing=True,
    )
