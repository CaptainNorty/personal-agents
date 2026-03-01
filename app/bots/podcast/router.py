import re

from fastapi import BackgroundTasks
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bots.podcast.agent import summarize_transcript
from app.bots.podcast.models import PodcastEpisode
from app.bots.podcast.spotify import resolve_spotify_url
from app.common.audio import transcribe_audio
from app.common.telegram import send_message, send_typing
from app.config import settings
from app.db.session import async_session

URL_PATTERN = re.compile(r"https?://\S+")
SPOTIFY_EPISODE_PATTERN = re.compile(r"https?://open\.spotify\.com/episode/\S+")


async def handle_message(
    chat_id: str, text: str, session: AsyncSession, background_tasks: BackgroundTasks
) -> None:
    """Handle an incoming message to the podcast bot."""
    token = settings.telegram_podcast_bot_token

    spotify_match = SPOTIFY_EPISODE_PATTERN.search(text)
    if spotify_match:
        url = spotify_match.group()
        await send_message(token, chat_id, "Resolving that Spotify link...")
        background_tasks.add_task(_process_spotify_episode, chat_id, url)
    elif URL_PATTERN.search(text):
        # Manual URL submission — start summarization directly
        url = URL_PATTERN.search(text).group()  # type: ignore[union-attr]
        await send_message(token, chat_id, "Got it! I'll work on summarizing that for you.")
        background_tasks.add_task(_process_episode, chat_id, url)
    elif text.strip().lower() in ("yes", "y"):
        # Reply to a new episode notification — find the most recent notified episode
        result = await session.execute(
            select(PodcastEpisode)
            .where(PodcastEpisode.status == "notified")
            .order_by(PodcastEpisode.created_at.desc())
            .limit(1)
        )
        episode = result.scalar_one_or_none()
        if episode:
            await send_message(token, chat_id, "On it! I'll summarize that episode for you.")
            background_tasks.add_task(_process_episode, chat_id, episode.audio_url, episode.id)
        else:
            await send_message(token, chat_id, "No pending episodes to summarize.")
    else:
        await send_message(token, chat_id, "Send me a podcast URL or reply 'yes' to a new episode notification.")


async def _process_episode(chat_id: str, audio_url: str, episode_id=None) -> None:
    """Background task: transcribe and summarize a podcast episode."""
    token = settings.telegram_podcast_bot_token
    try:
        await send_typing(token, chat_id)

        transcript = await transcribe_audio(audio_url)

        async with async_session() as session:
            if episode_id:
                result = await session.execute(
                    select(PodcastEpisode).where(PodcastEpisode.id == episode_id)
                )
                episode = result.scalar_one()
                episode.transcript = transcript
                episode.status = "summarizing"
                await session.commit()
            else:
                episode = PodcastEpisode(
                    feed_url="manual",
                    episode_title="Manual submission",
                    audio_url=audio_url,
                    transcript=transcript,
                    status="summarizing",
                )
                session.add(episode)
                await session.commit()
                episode_id = episode.id

            summary = await summarize_transcript(transcript)

            result = await session.execute(
                select(PodcastEpisode).where(PodcastEpisode.id == episode_id)
            )
            episode = result.scalar_one()
            episode.summary = summary
            episode.status = "complete"
            await session.commit()

        await send_message(token, chat_id, summary)
    except Exception:
        logger.exception(f"Failed to process episode: {audio_url}")
        await send_message(token, chat_id, "Sorry, something went wrong processing that episode.")


async def _process_spotify_episode(chat_id: str, spotify_url: str) -> None:
    """Background task: resolve a Spotify URL, then transcribe and summarize."""
    token = settings.telegram_podcast_bot_token
    try:
        audio_url = await resolve_spotify_url(spotify_url)
        await send_message(token, chat_id, "Found the audio. Transcribing now...")
        await _process_episode(chat_id, audio_url)
    except ValueError as exc:
        logger.warning(f"Spotify resolution failed for {spotify_url}: {exc}")
        await send_message(token, chat_id, f"Couldn't resolve that Spotify link: {exc}")
    except Exception:
        logger.exception(f"Failed to process Spotify episode: {spotify_url}")
        await send_message(token, chat_id, "Sorry, something went wrong processing that Spotify link.")
