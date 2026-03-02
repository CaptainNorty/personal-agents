from loguru import logger

from app.bots.nutrition.agent import _get_local_now, checkpointer, nutrition_agent
from app.common.scheduler import register_job
from app.common.telegram import send_message
from app.config import settings


async def send_eod_prompt() -> None:
    """Scheduled job: ask user if they have anything else to log before EOD summary."""
    chat_id = settings.owner_chat_id
    token = settings.telegram_nutrition_bot_token

    today = _get_local_now().strftime("%Y-%m-%d")
    thread_id = f"{chat_id}:{today}"

    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await nutrition_agent.ainvoke(
            {"messages": [{"role": "user", "content": "[SYSTEM:EOD_PROMPT]"}]},
            config=config,
        )
        response_text = result["messages"][-1].content
        await send_message(token, chat_id, response_text)
        logger.info("Sent EOD nutrition prompt")
    except Exception:
        logger.exception(f"EOD prompt failed on thread {thread_id}, resetting thread")
        if thread_id in checkpointer.storage:
            del checkpointer.storage[thread_id]


async def generate_eod_summary_timeout() -> None:
    """Scheduled job: generate and send daily summary after timeout."""
    chat_id = settings.owner_chat_id
    token = settings.telegram_nutrition_bot_token

    today = _get_local_now().strftime("%Y-%m-%d")
    thread_id = f"{chat_id}:{today}"

    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await nutrition_agent.ainvoke(
            {"messages": [{"role": "user", "content": "[SYSTEM:EOD_TIMEOUT]"}]},
            config=config,
        )
        response_text = result["messages"][-1].content
        await send_message(token, chat_id, response_text)
        logger.info("Sent EOD nutrition summary")
    except Exception:
        logger.exception(f"EOD summary failed on thread {thread_id}, resetting thread")
        if thread_id in checkpointer.storage:
            del checkpointer.storage[thread_id]


def register_nutrition_jobs() -> None:
    """Register end-of-day nutrition jobs."""
    register_job(
        send_eod_prompt,
        "cron",
        hour=21,
        minute=0,
        id="nutrition_eod_prompt",
        replace_existing=True,
    )
    register_job(
        generate_eod_summary_timeout,
        "cron",
        hour=21,
        minute=30,
        id="nutrition_eod_timeout",
        replace_existing=True,
    )
