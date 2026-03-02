from sqlalchemy.ext.asyncio import AsyncSession

from app.bots.nutrition.agent import _get_local_now, nutrition_agent
from app.common.telegram import send_message, send_typing
from app.config import settings


async def handle_message(chat_id: str, text: str, session: AsyncSession) -> None:
    """Handle an incoming message by invoking the nutrition agent."""
    token = settings.telegram_nutrition_bot_token
    await send_typing(token, chat_id)

    today = _get_local_now().strftime("%Y-%m-%d")
    thread_id = f"{chat_id}:{today}"

    result = await nutrition_agent.ainvoke(
        {"messages": [{"role": "user", "content": text}]},
        config={"configurable": {"thread_id": thread_id}},
    )

    response_text = result["messages"][-1].content
    await send_message(token, chat_id, response_text)
