from langchain.agents import create_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from loguru import logger
from sqlalchemy import select

from app.bots.podcast.models import PodcastEpisode
from app.common.llm import ask_claude, llm
from app.db.session import async_session

SUMMARIZE_SYSTEM_PROMPT = (
    "You are a podcast summarizer. Given a transcript, provide a concise summary "
    "including: key topics discussed, main arguments or insights, and any notable "
    "quotes. Keep it informative but brief."
)


async def summarize_transcript(transcript: str) -> str:
    """Summarize a podcast transcript using Claude."""
    return await ask_claude(transcript, system=SUMMARIZE_SYSTEM_PROMPT)


AGENT_SYSTEM_PROMPT = """\
You are a podcast Q&A assistant on Telegram. You help the user answer questions \
about podcasts they've previously transcribed.

When the user asks a question:
1. Use search_episodes to find relevant episodes (filter by show name and/or title keywords)
2. Use get_transcript to read the full transcript of the most relevant episode(s)
3. Answer the question based on the transcript content

Be concise and direct in your answers. Cite specific details from the transcript \
when possible. If you can't find a relevant episode or the transcript doesn't \
contain the answer, say so honestly.\
"""


@tool
async def search_episodes(
    show_name: str = "",
    episode_title: str = "",
    limit: int = 5,
) -> str:
    """Search previously transcribed podcast episodes. Filter by show_name and/or
    episode_title (both use case-insensitive partial matching). Returns the most
    recent matches first."""
    async with async_session() as session:
        query = select(PodcastEpisode).where(
            PodcastEpisode.transcript.isnot(None)
        )

        if show_name:
            query = query.where(PodcastEpisode.show_name.ilike(f"%{show_name}%"))
        if episode_title:
            query = query.where(PodcastEpisode.episode_title.ilike(f"%{episode_title}%"))

        query = query.order_by(PodcastEpisode.created_at.desc()).limit(limit)
        result = await session.execute(query)
        episodes = result.scalars().all()

    if not episodes:
        return "No transcribed episodes found matching your search."

    lines = []
    for ep in episodes:
        lines.append(
            f"ID: {ep.id} | Show: {ep.show_name or 'Unknown'} | "
            f"Title: {ep.episode_title} | Date: {ep.created_at.strftime('%Y-%m-%d')}"
        )
    return "\n".join(lines)


@tool
async def get_transcript(episode_id: str) -> str:
    """Retrieve the full transcript for a podcast episode by its ID."""
    async with async_session() as session:
        result = await session.execute(
            select(PodcastEpisode).where(PodcastEpisode.id == episode_id)
        )
        episode = result.scalar_one_or_none()

    if not episode:
        return f"No episode found with ID {episode_id}."
    if not episode.transcript:
        return f"Episode '{episode.episode_title}' has no transcript."

    transcript = episode.transcript
    if len(transcript) > 100_000:
        transcript = transcript[:100_000] + "\n\n[Transcript truncated at 100k characters]"

    header = (
        f"Show: {episode.show_name or 'Unknown'} | "
        f"Title: {episode.episode_title} | "
        f"Date: {episode.created_at.strftime('%Y-%m-%d')}\n\n"
    )
    return header + transcript


checkpointer = InMemorySaver()

podcast_agent = create_agent(
    model=llm,
    tools=[search_episodes, get_transcript],
    system_prompt=AGENT_SYSTEM_PROMPT,
    checkpointer=checkpointer,
)
