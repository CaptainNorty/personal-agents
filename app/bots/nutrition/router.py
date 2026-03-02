from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.bots.nutrition.agent import _get_local_now, checkpointer, nutrition_agent
from app.common.telegram import send_message, send_typing
from app.config import settings


async def handle_message(chat_id: str, text: str, session: AsyncSession) -> None:
    """Handle an incoming message by invoking the nutrition agent."""
    token = settings.telegram_nutrition_bot_token
    await send_typing(token, chat_id)

    today = _get_local_now().strftime("%Y-%m-%d")
    thread_id = f"{chat_id}:{today}"
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await nutrition_agent.ainvoke(
            {"messages": [{"role": "user", "content": text}]},
            config=config,
        )
        response_text = result["messages"][-1].content
    except Exception:
        logger.exception(f"Agent error on thread {thread_id}, resetting thread")
        # Clear the corrupted thread state and retry once
        if thread_id in checkpointer.storage:
            del checkpointer.storage[thread_id]
        try:
            result = await nutrition_agent.ainvoke(
                {"messages": [{"role": "user", "content": text}]},
                config=config,
            )
            response_text = result["messages"][-1].content
        except Exception:
            logger.exception("Agent error on retry")
            response_text = "Sorry, something went wrong. Please try again."

    await send_message(token, chat_id, response_text)
