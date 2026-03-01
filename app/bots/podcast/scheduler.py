from loguru import logger

from app.bots.podcast.feeds import check_feeds
from app.bots.podcast.models import PodcastEpisode
from app.common.scheduler import register_job
from app.common.telegram import send_message
from app.config import settings
from app.db.session import async_session


async def check_new_episodes() -> None:
    """Scheduled job: check RSS feeds for new episodes and notify."""
    async with async_session() as session:
        new_episodes = await check_feeds(session)
        token = settings.telegram_podcast_bot_token
        chat_id = settings.owner_chat_id

        for ep in new_episodes:
            episode = PodcastEpisode(
                feed_url=ep["feed_url"],
                episode_title=ep["episode_title"],
                audio_url=ep["audio_url"],
                published_at=ep["published_at"],
                status="notified",
            )
            session.add(episode)
            await session.commit()

            message = (
                f"{ep['feed_title']} just dropped a new episode: "
                f"{ep['episode_title']}. Want me to generate the summary?"
            )
            await send_message(token, chat_id, message)
            logger.info(f"Notified about new episode: {ep['episode_title']}")


def register_podcast_jobs() -> None:
    """Register podcast feed checking on an interval."""
    register_job(
        check_new_episodes,
        "interval",
        minutes=settings.podcast_check_interval_minutes,
        id="check_podcast_feeds",
        replace_existing=True,
    )
