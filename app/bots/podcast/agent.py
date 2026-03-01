from app.common.llm import ask_claude

SYSTEM_PROMPT = (
    "You are a podcast summarizer. Given a transcript, provide a concise summary "
    "including: key topics discussed, main arguments or insights, and any notable "
    "quotes. Keep it informative but brief."
)


async def summarize_transcript(transcript: str) -> str:
    """Summarize a podcast transcript using Claude."""
    return await ask_claude(transcript, system=SYSTEM_PROMPT)
