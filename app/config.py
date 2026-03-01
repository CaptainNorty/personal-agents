from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_agents"

    # Anthropic
    anthropic_api_key: str = ""

    # Telegram bot tokens
    telegram_podcast_bot_token: str = ""
    telegram_nutrition_bot_token: str = ""
    telegram_social_bot_token: str = ""

    # Telegram webhook base URL
    telegram_webhook_base_url: str = ""

    # Owner chat ID for proactive messages
    owner_chat_id: str = ""

    # Timezone
    timezone: str = "America/New_York"

    # Podcast settings
    podcast_feed_urls: str = ""
    podcast_check_interval_minutes: int = 30

    # Transcription
    deepgram_api_key: str = ""

    # App settings
    environment: str = "local"
    log_level: str = "DEBUG"

    @property
    def podcast_feeds(self) -> list[str]:
        """Parse comma-separated feed URLs."""
        if not self.podcast_feed_urls:
            return []
        return [url.strip() for url in self.podcast_feed_urls.split(",") if url.strip()]

    @property
    def bot_tokens(self) -> dict[str, str]:
        """Return a mapping of bot name to token."""
        return {
            "podcast": self.telegram_podcast_bot_token,
            "nutrition": self.telegram_nutrition_bot_token,
            "social": self.telegram_social_bot_token,
        }


settings = Settings()
