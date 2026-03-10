from loguru import logger

from app.bots.explainer.agent import checkpointer, explainer_agent
from app.bots.explainer.elevenlabs import text_to_speech
from app.common.telegram import send_message, send_typing, send_voice
from app.config import settings


async def handle_message(chat_id: str, text: str) -> None:
    """Handle an incoming message by generating an explanation, converting to speech, and sending both."""
    token = settings.telegram_explainer_bot_token
    await send_typing(token, chat_id)

    thread_id = f"explainer:{chat_id}"
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await explainer_agent.ainvoke(
            {"messages": [{"role": "user", "content": text}]},
            config=config,
        )
        explanation = result["messages"][-1].content
    except Exception:
        logger.exception(f"Explainer agent error on thread {thread_id}, resetting thread")
        if thread_id in checkpointer.storage:
            del checkpointer.storage[thread_id]
        try:
            result = await explainer_agent.ainvoke(
                {"messages": [{"role": "user", "content": text}]},
                config=config,
            )
            explanation = result["messages"][-1].content
        except Exception:
            logger.exception("Explainer agent error on retry")
            await send_message(token, chat_id, "Sorry, something went wrong. Please try again.")
            return

    try:
        audio_bytes = await text_to_speech(explanation)
        await send_voice(token, chat_id, audio_bytes)
    except Exception:
        logger.exception("TTS or voice send failed")

    await send_message(token, chat_id, explanation)
