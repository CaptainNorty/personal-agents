import httpx
from loguru import logger

from app.config import settings

ELEVENLABS_API = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE_ID = "nnGaEkFBVnWcgOmEgIdd"  # Uncle Iroh


async def text_to_speech(text: str) -> bytes:
    """Convert text to speech using ElevenLabs API. Returns OGG/Opus audio bytes."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{ELEVENLABS_API}/text-to-speech/{DEFAULT_VOICE_ID}",
            headers={
                "xi-api-key": settings.elevenlabs_api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
            },
            params={"output_format": "ogg_opus"},
        )
        if not resp.is_success:
            logger.error(f"ElevenLabs TTS failed: {resp.status_code} {resp.text}")
            raise RuntimeError(f"ElevenLabs TTS failed: {resp.status_code}")
        return resp.content
