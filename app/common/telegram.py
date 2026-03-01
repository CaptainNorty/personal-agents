from typing import Any

import httpx
from loguru import logger

from app.config import settings

TELEGRAM_API = "https://api.telegram.org"
MAX_MESSAGE_LENGTH = 4096


async def send_message(bot_token: str, chat_id: str, text: str) -> None:
    """Send a message via Telegram Bot API, chunking if over 4096 chars."""
    chunks = [text[i : i + MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
    async with httpx.AsyncClient() as client:
        for chunk in chunks:
            resp = await client.post(
                f"{TELEGRAM_API}/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": chunk},
            )
            if not resp.is_success:
                logger.error(f"Failed to send message: {resp.text}")


async def send_typing(bot_token: str, chat_id: str) -> None:
    """Send a 'typing' action indicator."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API}/bot{bot_token}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"},
        )


def parse_update(update: dict[str, Any]) -> tuple[str, str] | None:
    """Extract chat_id and text from a Telegram update. Returns None if not a text message."""
    message = update.get("message")
    if not message or "text" not in message:
        return None
    chat_id = str(message["chat"]["id"])
    text = message["text"]
    return chat_id, text


async def register_webhooks() -> None:
    """Register webhook URLs with Telegram for all configured bots."""
    base_url = settings.telegram_webhook_base_url
    if not base_url:
        logger.warning("TELEGRAM_WEBHOOK_BASE_URL not set — skipping webhook registration")
        return

    async with httpx.AsyncClient() as client:
        for bot_name, token in settings.bot_tokens.items():
            if not token:
                logger.warning(f"No token for {bot_name} bot — skipping webhook registration")
                continue
            webhook_url = f"{base_url}/webhooks/telegram/{bot_name}"
            resp = await client.post(
                f"{TELEGRAM_API}/bot{token}/setWebhook",
                json={"url": webhook_url},
            )
            if resp.is_success:
                logger.info(f"Registered webhook for {bot_name}: {webhook_url}")
            else:
                logger.error(f"Failed to register webhook for {bot_name}: {resp.text}")
