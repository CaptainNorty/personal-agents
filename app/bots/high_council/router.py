from loguru import logger

from app.bots.high_council.agent import checkpointer, council_agent
from app.bots.high_council.council import parse_conclusions
from app.bots.high_council.elevenlabs import generate_council_audio
from app.common.telegram import send_message, send_typing, send_voice
from app.config import settings


async def handle_message(chat_id: str, text: str) -> None:
    """Handle an incoming message by convening the High Council."""
    token = settings.telegram_high_council_bot_token
    await send_typing(token, chat_id)

    thread_id = f"high_council:{chat_id}"
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await council_agent.ainvoke(
            {"messages": [{"role": "user", "content": text}]},
            config=config,
        )
        response = result["messages"][-1].content
    except Exception:
        logger.exception(f"High Council agent error on thread {thread_id}, resetting thread")
        if thread_id in checkpointer.storage:
            del checkpointer.storage[thread_id]
        try:
            result = await council_agent.ainvoke(
                {"messages": [{"role": "user", "content": text}]},
                config=config,
            )
            response = result["messages"][-1].content
        except Exception:
            logger.exception("High Council agent error on retry")
            await send_message(token, chat_id, "Sorry, the council could not convene. Please try again.")
            return

    await send_message(token, chat_id, response)

    try:
        conclusions = parse_conclusions(response)
        if conclusions:
            audio_bytes = await generate_council_audio(conclusions)
            await send_voice(token, chat_id, audio_bytes)
        else:
            logger.warning("No conclusions parsed from council response")
    except Exception:
        logger.exception("Council audio generation or voice send failed")
