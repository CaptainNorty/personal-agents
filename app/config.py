from pathlib import Path

from pydantic_settings import BaseSettings

# Resolve .env relative to the repo root (this file lives at app/config.py),
# so launching the app from any CWD still finds the right file.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = {
        "env_file": str(_ENV_PATH),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_agents"

    # Anthropic
    anthropic_api_key: str = ""

    # Nutritionix API
    nutritionix_app_id: str = ""
    nutritionix_api_key: str = ""

    # Telegram bot tokens
    telegram_podcast_bot_token: str = ""
    telegram_nutrition_bot_token: str = ""
    telegram_social_bot_token: str = ""
    telegram_explainer_bot_token: str = ""
    telegram_high_council_bot_token: str = ""

    # Telegram webhook base URL
    telegram_webhook_base_url: str = ""

    # Owner chat ID for proactive messages
    owner_chat_id: str = ""

    # Timezone
    timezone: str = "America/New_York"

    # Podcast settings
    podcast_feed_urls: str = ""
    podcast_check_interval_minutes: int = 30

    # ElevenLabs TTS
    elevenlabs_api_key: str = ""

    # Transcription
    assemblyai_api_key: str = ""

    # PodcastIndex (for Spotify link resolution)
    podcastindex_api_key: str = ""
    podcastindex_api_secret: str = ""

    # App settings
    environment: str = "local"
    log_level: str = "DEBUG"

    # AWS / S3 — used by Unknown Unknowns for audio recording storage.
    # aws_profile is consumed only on local dev (boto3.Session(profile_name=...)).
    # In prod, set AWS_PROFILE="" in the EC2 .env so boto3 falls back to the
    # instance role.
    aws_profile: str = "personal"
    s3_bucket: str = ""
    s3_region: str = "us-east-2"

    # Firebase Admin SDK — service account JSON used to verify ID tokens.
    # Default resolves to <repo>/app/secrets/firebase-admin.json (gitignored).
    # Override in prod via env var.
    firebase_admin_key_path: str = str(
        _ENV_PATH.parent / "app" / "secrets" / "firebase-admin.json"
    )

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
            "explainer": self.telegram_explainer_bot_token,
            "high_council": self.telegram_high_council_bot_token,
        }


settings = Settings()
