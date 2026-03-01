from datetime import datetime

import feedparser
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bots.podcast.models import PodcastEpisode
from app.config import settings


async def check_feeds(session: AsyncSession) -> list[dict]:
    """Parse configured RSS feeds and return new (unseen) episodes."""
    new_episodes: list[dict] = []

    for feed_url in settings.podcast_feeds:
        try:
            feed = feedparser.parse(feed_url)
        except Exception:
            logger.exception(f"Failed to parse feed: {feed_url}")
            continue

        for entry in feed.entries:
            audio_url = _extract_audio_url(entry)
            if not audio_url:
                continue

            # Check if we already know about this episode
            existing = await session.execute(
                select(PodcastEpisode).where(PodcastEpisode.audio_url == audio_url)
            )
            if existing.scalar_one_or_none():
                continue

            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime(*entry.published_parsed[:6])

            episode_data = {
                "feed_url": feed_url,
                "episode_title": entry.get("title", "Untitled"),
                "audio_url": audio_url,
                "published_at": published_at,
                "feed_title": feed.feed.get("title", "Unknown Podcast"),
            }
            new_episodes.append(episode_data)

    return new_episodes


def _extract_audio_url(entry) -> str | None:
    """Extract the audio enclosure URL from a feed entry."""
    for link in entry.get("links", []):
        if link.get("type", "").startswith("audio/"):
            return link.get("href")
    for enclosure in entry.get("enclosures", []):
        if enclosure.get("type", "").startswith("audio/"):
            return enclosure.get("url")
    return None
