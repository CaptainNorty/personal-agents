from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.bots.nutrition import router as nutrition_router
from app.bots.podcast import router as podcast_router
from app.bots.social import router as social_router
from app.common.telegram import parse_update
from app.db.session import get_db

router = APIRouter(prefix="/webhooks/telegram", tags=["webhooks"])


@router.post("/{bot_name}")
async def telegram_webhook(
    bot_name: str,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Receive a Telegram webhook update and dispatch to the correct bot handler."""
    update = await request.json()
    parsed = parse_update(update)
    if not parsed:
        return {"ok": True}

    chat_id, text = parsed
    logger.info(f"[{bot_name}] Message from {chat_id}: {text[:50]}")

    if bot_name == "podcast":
        await podcast_router.handle_message(chat_id, text, session, background_tasks)
    elif bot_name == "nutrition":
        await nutrition_router.handle_message(chat_id, text, session)
    elif bot_name == "social":
        await social_router.handle_message(chat_id, text, session)
    else:
        logger.warning(f"Unknown bot name: {bot_name}")

    return {"ok": True}
